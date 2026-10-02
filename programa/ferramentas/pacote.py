"""Gera saida/app-X.Y.Z.zip (só o programa, sem o .exe) e saida/versao.json."""
import json
import os
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
versao = os.environ.get("VERSAO") or open(os.path.join(RAIZ, "app", "VERSION"), encoding="utf-8").read().strip()
saida = os.path.join(RAIZ, "saida")
os.makedirs(saida, exist_ok=True)
zip_ = os.path.join(saida, f"app-{versao}.zip")
with zipfile.ZipFile(zip_, "w", zipfile.ZIP_DEFLATED) as z:
    for pasta, dirs, arqs in os.walk(os.path.join(RAIZ, "app")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for a in arqs:
            if a.endswith(".pyc"):
                continue
            cam = os.path.join(pasta, a)
            z.write(cam, os.path.relpath(cam, RAIZ).replace(os.sep, "/"))
with open(os.path.join(saida, "versao.json"), "w", encoding="utf-8") as f:
    json.dump({"versao": versao, "launcher_minimo": int(os.environ.get("LAUNCHER") or 1),
               "notas": (os.environ.get("NOTAS") or "").strip()[:500]}, f, ensure_ascii=False)
print("ok", zip_, os.path.getsize(zip_), "bytes")
