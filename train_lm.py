#!/usr/bin/env python3
"""
Robust KenLM trainer: auto-adds --discount_fallback or drops to 3-gram
when tiny corpora make Modified Kneser-Ney blow up.
"""
import os, pathlib, subprocess, tempfile, sys, json, shutil, re, textwrap
from typing import Optional
from config import Settings

ROOT = pathlib.Path(__file__).parent
TEXT_DIR, LM_DIR = ROOT / "texts", ROOT / "lm";  LM_DIR.mkdir(exist_ok=True)

# -------- find KenLM tools exactly as in the previous answer ----------
def _find(tool:str)->Optional[pathlib.Path]:
    env=os.getenv("KENLM_BIN"); p=pathlib.Path
    if env and (p(env)/tool).is_file(): return p(env)/tool
    if (hit:=shutil.which(tool)): return p(hit)
    try:
        import importlib.resources as r, kenlm; wheel=p(r.files(kenlm))/ "bin"/ tool
        if wheel.is_file(): return wheel
    except Exception: pass
    return None

LMPLZ, BBIN = map(_find, ("lmplz","build_binary"))
if not LMPLZ or not BBIN:
    sys.exit("KenLM CLI tools not found – see previous instructions")

# ----------------------------------------------------------------------
PAT_BAD = re.compile(r"BadDiscountException")

def run_lmplz(order:int, corpus:str, arpa:str, fallback:bool=False)->bool:
    cmd = [str(LMPLZ), "-o", str(order)]
    if fallback: cmd.append("--discount_fallback")
    proc = subprocess.run(" ".join(cmd)+f" < {corpus} > {arpa}", shell=True,
                          stderr=subprocess.PIPE, text=True)
    if proc.returncode==0: return True
    if PAT_BAD.search(proc.stderr): return False        # signal retry
    proc.check_returncode()                             # raise other errors

def build(cfg:Settings):
    # concat corpus
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        for p in sorted(TEXT_DIR.glob("*.txt")): tmp.write(p.read_text()+"\n")
        corpus = tmp.name

    arpa, binary = LM_DIR/"model.arpa", LM_DIR/"model.binary"
    tried_fallback = False
    order = cfg.ngram_order

    while True:
        ok = run_lmplz(order, corpus, arpa, fallback=tried_fallback)
        if ok: break
        if not tried_fallback:
            print("↪︎ retrying with --discount_fallback …")
            tried_fallback = True
            continue
        if order>3:
            order = 3
            tried_fallback = False
            print("↪︎ corpus still too small → dropping to 3-gram …")
            continue
        sys.exit("💥 lmplz failed even after fallback; check your corpus")

    subprocess.run([str(BBIN), arpa, binary], check=True)
    pathlib.Path(corpus).unlink(); arpa.unlink()
    print(f"✅ built {binary} (order={order}, fallback={tried_fallback})")

if __name__ == "__main__":
    opts=json.loads(sys.argv[1]) if len(sys.argv)>1 else {}
    build(Settings(**opts))
