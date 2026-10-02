"""Ponto de entrada do programa Central de Obrigações."""
import json
import os
import sys
import time
import urllib.request
import webbrowser

from . import servidor
from .banco import Banco, semear

AQUI = os.path.dirname(os.path.abspath(__file__))


def versao():
    try:
        with open(os.path.join(AQUI, "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "0.0.0"


def pasta_usuario():
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    p = os.path.join(base, "CentralObrigacoes")
    os.makedirs(p, exist_ok=True)
    return p


def ler_cfg():
    try:
        with open(os.path.join(pasta_usuario(), "config.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def gravar_cfg(c):
    with open(os.path.join(pasta_usuario(), "config.json"), "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=1)


def pasta_dados():
    c = ler_cfg()
    return c.get("pastaDados") or os.path.join(pasta_usuario(), "dados")


def _salvar_pasta(p):
    c = ler_cfg()
    c["pastaDados"] = p
    gravar_cfg(c)


def _instancia_aberta():
    """Se o programa já está aberto, devolve a porta dele."""
    try:
        with open(os.path.join(pasta_usuario(), "porta.txt")) as f:
            porta = int(f.read().strip())
        with urllib.request.urlopen(f"http://127.0.0.1:{porta}/api/info", timeout=1.5) as r:
            if r.status == 200:
                return porta
    except Exception:  # noqa: BLE001
        pass
    return None


def rodar(sem_janela=False, porta_fixa=0):
    porta = _instancia_aberta()
    if porta and not sem_janela:
        webbrowser.open(f"http://127.0.0.1:{porta}/")
        return
    dados = pasta_dados()
    banco = Banco(dados)
    semear(banco, os.path.join(AQUI, "catalogo"))
    app = servidor.App(banco, dados, pasta_usuario(), versao(), _salvar_pasta)
    srv, porta = servidor.iniciar(app, porta_fixa)
    with open(os.path.join(pasta_usuario(), "porta.txt"), "w") as f:
        f.write(str(porta))
    url = f"http://127.0.0.1:{porta}/"
    if sem_janela:
        print(url, flush=True)
        while True:
            time.sleep(3600)
    try:
        import webview  # pywebview: janela própria do programa
        webview.create_window("Central de Obrigações", url, width=1360, height=860, min_size=(900, 600))
        webview.start()
    except Exception:  # noqa: BLE001  sem pywebview/WebView2: abre no navegador e fica rodando
        webbrowser.open(url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
    srv.shutdown()


if __name__ == "__main__":
    rodar("--sem-janela" in sys.argv)
