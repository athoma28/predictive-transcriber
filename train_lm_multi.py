#!/usr/bin/env python3
"""
Rebuilds N different KenLM models according to config.MODELS.
Char models space-separate every character so KenLM treats them as tokens.
"""
import pathlib, subprocess, tempfile, json, os, shutil, textwrap, sys, re
from typing import Optional
from config import MODELS

ROOT     = pathlib.Path(__file__).parent
TEXT_DIR = ROOT / "texts"
LM_DIR   = ROOT / "lm";  LM_DIR.mkdir(exist_ok=True)

# ---- locate KenLM binaries (same helper as before) -------------------------
def _find(tool:str)->Optional[pathlib.Path]:
    import importlib.resources as r, kenlm
    env=os.getenv("KENLM_BIN"); p=pathlib.Path
    if env and (p(env)/tool).is_file(): return p(env)/tool
    if (hit:=shutil.which(tool)): return p(hit)
    wheel=p(r.files(kenlm))/ "bin"/ tool
    return wheel if wheel.is_file() else None

LMPLZ, BBIN = map(_find, ("lmplz","build_binary"))
if not LMPLZ or not BBIN:
    sys.exit("KenLM CLI tools not found; set PATH or KENLM_BIN")

# ---- preprocessing helpers -------------------------------------------------
TOKEN_RE = re.compile(r"\S+")
def char_line(line:str)->str:
    return " ".join(list(line.rstrip("\n")))

def build_one(spec):
    corpus_fd = tempfile.NamedTemporaryFile(mode="w+", delete=False)
    for p in sorted(TEXT_DIR.glob("*.txt")):
        for line in p.read_text(encoding="utf-8").splitlines():
            corpus_fd.write(char_line(line) if spec.char else line)
            corpus_fd.write("\n")
    corpus_fd.close()

    arpa   = LM_DIR / f"{spec.id}.arpa"
    binary = LM_DIR / f"{spec.id}.binary"

    cmd = [str(LMPLZ), "-o", str(spec.order), "--discount_fallback"]

    subprocess.run(" ".join(cmd) + f" < {corpus_fd.name} > {arpa}",
                   shell=True, check=True)
    subprocess.run([str(BBIN), arpa, binary], check=True)
    os.unlink(corpus_fd.name); arpa.unlink()
    print(f"✅ {spec.id} → {binary}")

if __name__ == "__main__":
    for spec in MODELS:
        build_one(spec)
