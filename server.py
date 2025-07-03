#!/usr/bin/env python3
import pathlib, subprocess, threading, time, json, logging, os, re
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import kenlm
from config import MODELS

ROOT   = pathlib.Path(__file__).parent
TEXT   = ROOT / "texts"
LM_DIR = ROOT / "lm"
TOKEN_RE = re.compile(r"\S+")

app = FastAPI()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

# ---------- load all models & vocabs ----------------------------------------
def load_models():
    objs, vocabs = {}, {}
    for spec in MODELS:
        path = LM_DIR / f"{spec.id}.binary"
        objs[spec.id] = kenlm.Model(str(path))
    # vocab per model (word or char)
    vocabs["word"] = sorted({tok for p in TEXT.glob("*.txt")
                             for tok in TOKEN_RE.findall(p.read_text())})
    vocabs["char"] = sorted({ch for p in TEXT.glob("*.txt")
                             for ch in p.read_text() if ch != " "})   # ← drop space
    return objs, vocabs

models, vocabs = load_models()

# ---------- API schemas ------------------------------------------------------
class Settings(BaseModel):
    context_window: int = 20
    top_k:          int = 5

class PredictRequest(BaseModel):
    context: str
    settings: Settings = Settings()

# ---------- endpoints --------------------------------------------------------
@app.post("/predict")
def predict(req: PredictRequest):
    if not req.context.strip():
        raise HTTPException(status_code=400, detail="Context empty")
    ctx_words = req.context.strip().split()[-req.settings.context_window :]
    ctx_chars = list(req.context)[-req.settings.context_window :]

    results = {"word": [], "char": []}
    for spec in MODELS:
        if spec.char:
            continue
        ctx = ctx_words
        vocab = vocabs["word"]
        scored = []
        for tok in vocab:
            s = models[spec.id].score(" ".join(ctx + [tok]),
                                      bos=False, eos=False)
            scored.append((s, tok))
        scored.sort(reverse=True)
    top = [w for _, w in scored if w.strip() and len(w) > 1]
    results["word"].extend(top[: req.settings.top_k])

    seen, agg = set(), []
    for w in results["word"]:
        if w not in seen:
            seen.add(w); agg.append(w)
    return {"merged": agg[: req.settings.top_k]}

# ---------- retrain on save --------------------------------------------------
class SaveRequest(BaseModel):
    filename: str
    text: str
    settings: Settings = Settings()

def background_retrain():
    subprocess.run(["python", str(ROOT / "train_lm_multi.py")], check=True)
    global models, vocabs
    models, vocabs = load_models()
    logging.info("All models rebuilt & hot-swapped")

@app.post("/save")
def save(req: SaveRequest):
    if "/" in req.filename or req.filename.startswith("."):
        raise HTTPException(status_code=400, detail="Bad filename")
    (TEXT / req.filename).write_text(req.text, encoding="utf-8")
    threading.Thread(target=background_retrain, daemon=True).start()
    return {"saved": req.filename}

# ---------- static files -----------------------------------------------------
@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT.parent / "web" / "index.html")

app.mount("/static", StaticFiles(directory=str(ROOT.parent / "web")), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
