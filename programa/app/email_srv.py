"""Envio (SMTP) e leitura de respostas (IMAP) com qualquer provedor de e-mail."""
import base64
import email
import email.policy
import email.utils
import imaplib
import json
import os
import re
import smtplib
import ssl
import sys
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from email.message import EmailMessage

PROVEDORES = {
    "gmail": {"nome": "Gmail / Google Workspace", "smtp": "smtp.gmail.com", "smtp_porta": 465, "smtp_seg": "ssl",
              "imap": "imap.gmail.com", "imap_porta": 993,
              "dica": "Use uma senha de app (Conta Google > Segurança > Verificação em duas etapas > Senhas de app)."},
    "outlook": {"nome": "Outlook / Microsoft 365", "smtp": "smtp.office365.com", "smtp_porta": 587, "smtp_seg": "starttls",
                "imap": "outlook.office365.com", "imap_porta": 993,
                "dica": "A Microsoft está desligando o login por senha simples (SMTP AUTH). Pode ser preciso o administrador liberar SMTP AUTH na conta."},
    "yahoo": {"nome": "Yahoo", "smtp": "smtp.mail.yahoo.com", "smtp_porta": 465, "smtp_seg": "ssl",
              "imap": "imap.mail.yahoo.com", "imap_porta": 993, "dica": "Use uma senha de app do Yahoo."},
    "locaweb": {"nome": "Locaweb", "smtp": "email-ssl.com.br", "smtp_porta": 465, "smtp_seg": "ssl",
                "imap": "email-ssl.com.br", "imap_porta": 993, "dica": ""},
    "hostgator": {"nome": "HostGator", "smtp": "mail.SEUDOMINIO.com.br", "smtp_porta": 465, "smtp_seg": "ssl",
                  "imap": "mail.SEUDOMINIO.com.br", "imap_porta": 993, "dica": "Troque SEUDOMINIO pelo domínio do escritório."},
    "outro": {"nome": "Outro provedor", "smtp": "", "smtp_porta": 465, "smtp_seg": "ssl", "imap": "", "imap_porta": 993,
              "dica": "Pegue os dados de SMTP e IMAP com o provedor do e-mail."},
}


# ---------- senha guardada com proteção do Windows (DPAPI) ----------
def _dpapi(dados, proteger):
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(dados, len(dados))
    entrada = BLOB(len(dados), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    saida = BLOB()
    f = ctypes.windll.crypt32.CryptProtectData if proteger else ctypes.windll.crypt32.CryptUnprotectData
    if not f(ctypes.byref(entrada), None, None, None, None, 0, ctypes.byref(saida)):
        raise OSError("Falha ao proteger a senha")
    try:
        return ctypes.string_at(saida.pbData, saida.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(saida.pbData)


def cifrar(senha):
    b = senha.encode("utf-8")
    if sys.platform == "win32":
        return "dpapi:" + base64.b64encode(_dpapi(b, True)).decode()
    return "b64:" + base64.b64encode(b).decode()


def decifrar(s):
    if not s:
        return ""
    tipo, _, val = s.partition(":")
    raw = base64.b64decode(val)
    if tipo == "dpapi":
        return _dpapi(raw, False).decode("utf-8")
    return raw.decode("utf-8")


# ---------- configuração (fica no computador de cada usuário, não na pasta compartilhada) ----------
class ConfigEmail:
    def __init__(self, pasta_usuario):
        self.arq = os.path.join(pasta_usuario, "email.json")

    def ler(self, com_senha=False):
        try:
            with open(self.arq, encoding="utf-8") as f:
                c = json.load(f)
        except (OSError, ValueError):
            c = {}
        if com_senha:
            c["senha"] = decifrar(c.get("senha_cifrada", ""))
        c["tem_senha"] = bool(c.get("senha_cifrada"))
        if not com_senha:
            c.pop("senha_cifrada", None)
        return c

    def gravar(self, dados):
        atual = {}
        try:
            with open(self.arq, encoding="utf-8") as f:
                atual = json.load(f)
        except (OSError, ValueError):
            pass
        for k in ("provedor", "remetente", "nome_remetente", "usuario", "smtp", "smtp_porta", "smtp_seg",
                  "imap", "imap_porta", "copia_para"):
            if k in dados:
                atual[k] = dados[k]
        if dados.get("senha"):
            atual["senha_cifrada"] = cifrar(dados["senha"])
        os.makedirs(os.path.dirname(self.arq), exist_ok=True)
        with open(self.arq, "w", encoding="utf-8") as f:
            json.dump(atual, f, ensure_ascii=False, indent=1)


def _smtp(c):
    ctx = ssl.create_default_context()
    porta = int(c.get("smtp_porta") or 465)
    if (c.get("smtp_seg") or "ssl") == "ssl":
        s = smtplib.SMTP_SSL(c["smtp"], porta, context=ctx, timeout=40)
    else:
        s = smtplib.SMTP(c["smtp"], porta, timeout=40)
        s.ehlo()
        s.starttls(context=ctx)
        s.ehlo()
    s.login(c.get("usuario") or c["remetente"], c["senha"])
    return s


def _imap(c):
    m = imaplib.IMAP4_SSL(c["imap"], int(c.get("imap_porta") or 993), ssl_context=ssl.create_default_context())
    m.login(c.get("usuario") or c["remetente"], c["senha"])
    return m


def testar(c):
    erros = []
    try:
        s = _smtp(c)
        s.quit()
    except Exception as e:  # noqa: BLE001
        erros.append(f"Envio (SMTP): {e}")
    if c.get("imap"):
        try:
            m = _imap(c)
            m.logout()
        except Exception as e:  # noqa: BLE001
            erros.append(f"Leitura (IMAP): {e}")
    return erros


def montar(c, para, assunto, html, texto, anexos=(), responder_a=None):
    msg = EmailMessage()
    msg["From"] = email.utils.formataddr((c.get("nome_remetente") or "", c["remetente"]))
    msg["To"] = ", ".join(para)
    if c.get("copia_para"):
        msg["Bcc"] = c["copia_para"]
    msg["Subject"] = assunto
    msg["Date"] = email.utils.formatdate(localtime=True)
    dominio = c["remetente"].split("@")[-1]
    msg["Message-ID"] = email.utils.make_msgid(domain=dominio)
    if responder_a:
        msg["In-Reply-To"] = responder_a
        msg["References"] = responder_a
    msg.set_content(texto)
    msg.add_alternative(html, subtype="html")
    for nome, dados in anexos:
        msg.add_attachment(dados, maintype="application", subtype="pdf", filename=nome)
    return msg


def enviar(c, msgs):
    """Envia uma lista de mensagens numa conexão só. Devolve [(ok, erro)]."""
    s = _smtp(c)
    res = []
    try:
        for m in msgs:
            try:
                s.send_message(m)
                res.append((True, None))
            except Exception as e:  # noqa: BLE001
                res.append((False, str(e)))
                break
    finally:
        try:
            s.quit()
        except Exception:  # noqa: BLE001
            pass
    return res


def _dec(v):
    try:
        return str(make_header(decode_header(v or "")))
    except Exception:  # noqa: BLE001
        return v or ""


def _corpo_texto(msg):
    if msg.is_multipart():
        for p in msg.walk():
            if p.get_content_type() == "text/plain" and not p.get_filename():
                try:
                    return p.get_content()
                except Exception:  # noqa: BLE001
                    return (p.get_payload(decode=True) or b"").decode("utf-8", "replace")
        for p in msg.walk():
            if p.get_content_type() == "text/html":
                h = (p.get_payload(decode=True) or b"").decode("utf-8", "replace")
                return re.sub(r"<[^>]+>", " ", h)
        return ""
    try:
        return msg.get_content()
    except Exception:  # noqa: BLE001
        return (msg.get_payload(decode=True) or b"").decode("utf-8", "replace")


def sem_citacao(texto):
    """Corta o histórico citado ('Em ... escreveu:', linhas com '>')."""
    linhas = []
    for l in texto.splitlines():
        ls = l.strip()
        if ls.startswith(">"):
            break
        if re.match(r"^(Em|On) .+(escreveu|wrote):?$", ls) or ls.startswith("-----Original") \
                or re.match(r"^(De|From):\s", ls):
            break
        linhas.append(l)
    return re.sub(r"\s+", " ", " ".join(linhas)).strip()[:400]


def buscar_respostas(c, envios, dias=60):
    """envios: [{protocolo, messageId, enviadoEm}]. Procura na Caixa de Entrada respostas posteriores.

    Devolve {protocolo: {cienteEm, cienteDe, resposta}}.
    """
    meu = (c["remetente"] or "").lower()
    achados = {}
    m = _imap(c)
    try:
        m.select("INBOX", readonly=True)
        desde = (datetime.now() - timedelta(days=dias)).strftime("%d-%b-%Y")
        for e in envios:
            prot = e["protocolo"]
            typ, data = m.search(None, f'(SINCE {desde} SUBJECT "{prot}")')
            ids = data[0].split() if typ == "OK" and data and data[0] else []
            candidatos = []
            for i in ids:
                typ, d = m.fetch(i, "(RFC822)")
                if typ != "OK" or not d or not isinstance(d[0], tuple):
                    continue
                msg = email.message_from_bytes(d[0][1], policy=email.policy.default)
                de = email.utils.parseaddr(_dec(msg.get("From")))[1].lower()
                if not de or de == meu:
                    continue
                try:
                    quando = email.utils.parsedate_to_datetime(msg.get("Date"))
                    quando = quando.astimezone().replace(tzinfo=None)
                except Exception:  # noqa: BLE001
                    continue
                enviado = datetime.fromisoformat(e["enviadoEm"][:19])
                if quando < enviado:
                    continue
                refs = (msg.get("In-Reply-To") or "") + " " + (msg.get("References") or "")
                peso = 0 if (e.get("messageId") and e["messageId"] in refs) else 1
                candidatos.append((peso, quando, de, sem_citacao(_corpo_texto(msg))))
            if candidatos:
                candidatos.sort()
                _, quando, de, txt = candidatos[0]
                achados[prot] = {"cienteEm": quando.strftime("%Y-%m-%dT%H:%M:%S"), "cienteDe": de, "resposta": txt}
    finally:
        try:
            m.logout()
        except Exception:  # noqa: BLE001
            pass
    return achados
