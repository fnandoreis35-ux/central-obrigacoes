"""Teste ponta a ponta: servidor real + navegador (Playwright), com SMTP/IMAP simulados."""
import email
import email.utils
import os
import shutil
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import email_srv, servidor  # noqa: E402
from app.banco import Banco, semear  # noqa: E402

T = "/tmp/claude-0/t"
BASE = "/tmp/claude-0/e2e"
shutil.rmtree(BASE, ignore_errors=True)
os.makedirs(BASE)

ENVIADOS = []


class FakeSMTP:
    def send_message(self, m):
        ENVIADOS.append(m)

    def quit(self):
        pass


class FakeIMAP:
    """Devolve, para cada protocolo enviado, uma resposta do cliente."""

    def select(self, *a, **k):
        return "OK", [b"1"]

    def search(self, _c, crit):
        ids = [str(i + 1).encode() for i, m in enumerate(ENVIADOS) if m["Subject"].split("Protocolo ")[-1] in crit]
        return "OK", [b" ".join(ids)]

    def fetch(self, i, _):
        orig = ENVIADOS[int(i) - 1]
        r = email.message.EmailMessage()
        r["From"] = "Cliente <" + orig["To"].split(",")[0].strip() + ">"
        r["Subject"] = "Re: " + orig["Subject"]
        r["Date"] = email.utils.format_datetime((datetime.now() + timedelta(minutes=5)).astimezone())
        r["In-Reply-To"] = orig["Message-ID"]
        r.set_content("RECEBIDO, obrigado!\n\nEm qua, escreveu:\n> Seguem as guias")
        return "OK", [(b"1", r.as_bytes())]

    def logout(self):
        pass


email_srv._smtp = lambda c: FakeSMTP()
email_srv._imap = lambda c: FakeIMAP()

banco = Banco(os.path.join(BASE, "dados"))
semear(banco, os.path.join(os.path.dirname(__file__), "..", "app", "catalogo"))
cfg = banco.obter("config", "escritorio")
cfg["nome"] = "Escritório Teste"
banco.set("config", "escritorio", cfg)
banco.set("clientes", "12345678000190", {"nome": "ACME LTDA", "cnpj": "12345678000190", "regime": "Simples Nacional",
                                         "emails": ["financeiro@acme.com"], "resp": "Ana", "obrigacoes": ["das", "fgts", "pgdas"], "ativo": True})
app = servidor.App(banco, os.path.join(BASE, "dados"), os.path.join(BASE, "usuario"), "1.0.0")
app.cfg_email.gravar({"provedor": "gmail", "remetente": "guias@escritorio.com", "nome_remetente": "Escritório Teste",
                      "smtp": "smtp.gmail.com", "smtp_porta": 465, "smtp_seg": "ssl", "imap": "imap.gmail.com", "imap_porta": 993,
                      "senha": "segredo"})
assert app.cfg_email.ler(com_senha=True)["senha"] == "segredo"
srv, porta = servidor.iniciar(app, 0)
URL = f"http://127.0.0.1:{porta}/"

from playwright.sync_api import sync_playwright  # noqa: E402

erros_js = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1400, "height": 900})
    pg.on("pageerror", lambda e: erros_js.append(str(e)))
    pg.goto(URL)
    pg.wait_for_selector("text=Agenda da competência")
    # competência 09/2026 e gerar tarefas
    pg.fill("#f-newcomp", "2026-09")
    pg.dispatch_event("#f-newcomp", "change")
    pg.wait_for_selector("text=Agenda da competência 09/2026")
    pg.click("button:has-text('Gerar tarefas de 09/2026')")
    pg.click("button:has-text('Gerar 3 tarefas')")
    pg.wait_for_selector("text=Vence")
    time.sleep(1)
    tarefa = banco.obter("tarefas", "2026-09_12345678000190")
    print("tarefa itens:", {k: v["venc"] for k, v in tarefa["itens"].items()})
    assert tarefa["itens"]["das"]["venc"] == "2026-10-20"
    pg.screenshot(path=f"{BASE}/1-agenda.png")

    # enviar guias
    pg.click("nav >> text=Enviar guias")
    pg.set_input_files("#g-arqs", [f"{T}/DAS_ACME.pdf", f"{T}/FGTS_ACME.pdf", f"{T}/DARF_XYZ.pdf"])
    pg.click("button:has-text('Ler guias')")
    pg.wait_for_selector("text=Serão enviados 1 e-mail(s)")
    pg.screenshot(path=f"{BASE}/2-guias.png", full_page=True)
    pg.click("button:has-text('Enviar 1 e-mail(s)')")
    pg.click("button:has-text('Sim, enviar')")
    pg.wait_for_selector("text=Resultado do envio")
    pg.screenshot(path=f"{BASE}/3-enviado.png", full_page=True)
    assert len(ENVIADOS) == 1, ENVIADOS
    m = ENVIADOS[0]
    print("Assunto:", m["Subject"], "| Para:", m["To"])
    anexos = [part.get_filename() for part in m.iter_attachments()]
    print("Anexos:", anexos)
    assert len(anexos) == 2 and "PRT-202609-0001" in m["Subject"]
    t = banco.obter("tarefas", "2026-09_12345678000190")
    assert t["itens"]["das"]["status"] == "enviada" and t["envios"][0]["status"] == "aguardando"

    # protocolos: conferir ciência
    pg.click("nav >> text=Protocolos")
    pg.click("button:has-text('Conferir respostas dos clientes')")
    pg.wait_for_selector("text=nova(s) ciência(s)")
    time.sleep(3)
    t = banco.obter("tarefas", "2026-09_12345678000190")
    print("ciência:", t["envios"][0]["status"], t["envios"][0]["cienteDe"], repr(t["envios"][0]["resposta"]))
    assert t["envios"][0]["status"] == "ciente" and t["itens"]["das"]["status"] == "ciente"
    assert t["envios"][0]["resposta"] == "RECEBIDO, obrigado!"
    pg.click("button:has-text('Todos')")
    pg.screenshot(path=f"{BASE}/4-protocolos.png", full_page=True)

    # importar clientes
    pg.click("nav >> text=Clientes")
    pg.set_input_files("#imp-arq", f"{T}/carteira.xlsx")
    pg.wait_for_selector("text=Importar clientes")
    pg.screenshot(path=f"{BASE}/5-importar.png")
    pg.click("button:has-text('Importar 3')")
    pg.wait_for_selector("text=BETA COMERCIO")
    beta = banco.obter("clientes", "11222333000181")
    acme = banco.obter("clientes", "12345678000190")
    print("beta:", beta["regime"], beta["emails"], len(beta["obrigacoes"]), "| acme emails mantidos:", acme["emails"])
    assert acme["emails"] == ["financeiro@acme.com"]

    # configurações / e-mail
    pg.click("nav >> text=Configurações")
    pg.wait_for_selector("text=E-mail de envio das guias")
    pg.screenshot(path=f"{BASE}/6-config.png", full_page=True)

    # cobrança: reabrir ciência e cobrar
    t = banco.obter("tarefas", "2026-09_12345678000190")
    t["envios"][0]["status"] = "aguardando"
    banco.set("tarefas", "2026-09_12345678000190", t)
    app.cobrar({"tarefaId": "2026-09_12345678000190", "idx": 0})
    print("cobrança:", ENVIADOS[-1]["Subject"], ENVIADOS[-1]["In-Reply-To"] == ENVIADOS[0]["Message-ID"])
    b.close()

print("Erros JS:", erros_js)
assert not erros_js
print("TUDO OK")
srv.shutdown()
