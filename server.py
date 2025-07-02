# app/server.py

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import kenlm, pathlib, subprocess, threading, time, json, re, logging, os

ROOT      = pathlib.Path(__file__).parent
TEXT_DIR  = ROOT / "texts"
MODEL_BIN = ROOT / "lm" / "model.binary"
TOKEN_RE  = re.compile(r"\S+")        # naive whitespace tokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
app = FastAPI()

# ----------------------------------------------------------------------
def build_vocab() -> list[str]:
    """Collect all distinct tokens from every .txt file in texts/."""
    vocab = set()
    for path in TEXT_DIR.glob("*.txt"):
        vocab.update(TOKEN_RE.findall(path.read_text(encoding="utf-8")))
    return sorted(vocab)

def load_model():
    if not MODEL_BIN.exists():
        raise RuntimeError("No KenLM model. Run train_lm.py first.")
    return kenlm.Model(str(MODEL_BIN))

lm     = load_model()
vocab  = build_vocab()

# ----------------------------------------------------------------------
class Settings(BaseModel):
    context_window: int = 20
    top_k:          int = 5

class PredictRequest(BaseModel):
    context: str
    settings: Settings = Settings()

class SaveRequest(BaseModel):
    filename: str
    text: str
    settings: Settings = Settings()

# ----------------------------------------------------------------------
@app.post("/predict")
def predict(req: PredictRequest):
    if not req.context.strip():
        raise HTTPException(status_code=400, detail="Context cannot be empty")
    words = req.context.strip().split()[-req.settings.context_window :]
    scored = []
    for w in vocab:
        s = lm.score(" ".join(words + [w]), bos=False, eos=False)
        scored.append((s, w))
    scored.sort(reverse=True)
    return {"suggestions": [w for _, w in scored[: req.settings.top_k]]}

# ----------------------------------------------------------------------
def retrain(settings: Settings):
    def _job():
        t0 = time.time()
        subprocess.run(
            ["python", str(ROOT / "train_lm.py"), json.dumps(settings.dict())],
            check=True)
        global lm, vocab
        lm    = load_model()
        vocab = build_vocab()
        logging.info("Model + vocab rebuilt in %.2fs", time.time() - t0)
    threading.Thread(target=_job, daemon=True).start()

@app.post("/save")
def save(req: SaveRequest):
    if "/" in req.filename or req.filename.startswith("."):
        raise HTTPException(status_code=400, detail="Bad filename")
    path = TEXT_DIR / req.filename
    path.write_text(req.text, encoding="utf-8")
    retrain(req.settings)
    return {"saved": path.name}

# ----------------------------------------------------------------------
@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT.parent / "web" / "index.html")

# mount static LAST so it’s only a fallback
app.mount("/static", StaticFiles(directory=str(ROOT.parent / "web")), name="static")

# convenience: run directly with `python app/server.py`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
