"""Inicializador da Central de Obrigações.

Este arquivo vira o CentralObrigacoes.exe. Ele quase nunca muda: a cada abertura
consulta o GitHub e, se houver versão nova do programa, baixa só o pacote do
programa (alguns KB) e passa a usá-lo. Os dados do escritório não são tocados.
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import urllib.request
import zipfile

# Bibliotecas usadas pelo pacote do programa: importadas aqui para entrarem no .exe.
import base64, csv, ctypes, datetime, email, email.header, email.message, email.policy, email.utils  # noqa: E401,F401
import http.server, imaplib, io, mimetypes, re, smtplib, sqlite3, ssl, time, traceback, uuid, webbrowser  # noqa: E401,F401
import urllib.parse  # noqa: F401
import pypdf  # noqa: F401
import openpyxl  # noqa: F401
try:
    import webview  # noqa: F401
except Exception:  # noqa: BLE001
    webview = None

LAUNCHER_VERSAO = 1
REPO = "fnandoreis35-ux/central-obrigacoes"
API = f"https://api.github.com/repos/{REPO}/releases/latest"


def base():
    p = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "CentralObrigacoes")
    os.makedirs(p, exist_ok=True)
    return p


def aviso(texto, titulo="Central de Obrigações"):
    try:
        ctypes.windll.user32.MessageBoxW(None, texto, titulo, 0x40)
    except Exception:  # noqa: BLE001
        print(texto)


def vtuple(v):
    try:
        return tuple(int(x) for x in str(v).strip().lstrip("v").split("."))
    except ValueError:
        return (0,)


def ler_versao(pasta_app):
    try:
        with open(os.path.join(pasta_app, "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "0.0.0"


def pasta_embutida():
    raiz = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    for c in (os.path.join(raiz, "app_embutido", "app"), os.path.join(raiz, "..", "app")):
        if os.path.isfile(os.path.join(c, "VERSION")):
            return os.path.abspath(c)
    raise RuntimeError("Pacote do programa não encontrado")


def pasta_instalada():
    """Pacote mais recente baixado: <base>/versoes/<versão>/app"""
    try:
        with open(os.path.join(base(), "versao_atual.txt"), encoding="utf-8") as f:
            v = f.read().strip()
        p = os.path.join(base(), "versoes", v, "app")
        if os.path.isfile(os.path.join(p, "VERSION")):
            return p
    except OSError:
        pass
    return None


def escolher_pacote():
    emb = pasta_embutida()
    inst = pasta_instalada()
    if inst and vtuple(ler_versao(inst)) > vtuple(ler_versao(emb)):
        return inst
    return emb


def _get(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": "CentralObrigacoes", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def procurar_atualizacao(versao_atual):
    """Baixa e instala o pacote novo, se existir. Devolve a pasta nova ou None."""
    try:
        rel = json.loads(_get(API, 6))
    except Exception:  # noqa: BLE001  sem internet: segue com a versão atual
        return None
    assets = {a["name"]: a["browser_download_url"] for a in rel.get("assets") or []}
    if "versao.json" not in assets:
        return None
    try:
        info = json.loads(_get(assets["versao.json"], 10))
    except Exception:  # noqa: BLE001
        return None
    nova = info.get("versao", "0")
    if vtuple(nova) <= vtuple(versao_atual):
        return None
    if int(info.get("launcher_minimo", 1)) > LAUNCHER_VERSAO:
        aviso(f"Há uma versão nova da Central de Obrigações ({nova}) que precisa do instalador novo.\n\n"
              f"Baixe em: https://github.com/{REPO}/releases/latest\n\nVocê pode continuar usando a versão atual.")
        return None
    nome_zip = f"app-{nova}.zip"
    if nome_zip not in assets:
        return None
    destino = os.path.join(base(), "versoes", nova)
    tmp = tempfile.mkdtemp(prefix="co-")
    try:
        arq = os.path.join(tmp, nome_zip)
        with open(arq, "wb") as f:
            f.write(_get(assets[nome_zip], 60))
        with zipfile.ZipFile(arq) as z:
            for n in z.namelist():  # proteção contra caminhos fora da pasta
                if n.startswith("/") or ".." in n.split("/"):
                    raise RuntimeError("Pacote inválido")
            shutil.rmtree(destino, ignore_errors=True)
            z.extractall(destino)
        if ler_versao(os.path.join(destino, "app")) != nova:
            raise RuntimeError("Versão do pacote não confere")
        with open(os.path.join(base(), "versao_atual.txt"), "w", encoding="utf-8") as f:
            f.write(nova)
        limpar_antigas(nova)
        return os.path.join(destino, "app"), info.get("notas", "")
    except Exception as e:  # noqa: BLE001
        print("Falha na atualização:", e)
        shutil.rmtree(destino, ignore_errors=True)
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def limpar_antigas(manter):
    pasta = os.path.join(base(), "versoes")
    try:
        vs = sorted(os.listdir(pasta), key=vtuple)
        for v in vs[:-2]:
            if v != manter:
                shutil.rmtree(os.path.join(pasta, v), ignore_errors=True)
    except OSError:
        pass


def main():
    log = open(os.path.join(base(), "programa.log"), "a", encoding="utf-8", buffering=1)
    if sys.stdout is None or getattr(sys, "frozen", False):
        sys.stdout = sys.stderr = log
    pacote = escolher_pacote()
    if "--sem-atualizar" not in sys.argv:
        r = procurar_atualizacao(ler_versao(pacote))
        if r:
            pacote, notas = r
            threading.Thread(target=aviso, args=(f"A Central de Obrigações foi atualizada para a versão {ler_versao(pacote)}."
                                                 + (f"\n\n{notas}" if notas else ""),), daemon=True).start()
    sys.path.insert(0, os.path.dirname(pacote))
    for m in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[m]
    from app import main as programa  # noqa: E402
    programa.rodar()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        aviso(f"Não foi possível abrir a Central de Obrigações.\n\n{e}\n\nDetalhes em {os.path.join(base(), 'programa.log')}")
