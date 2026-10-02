"""Leitura das guias em PDF (DAS, DARF, FGTS, ICMS, ISS) e identificação de cliente e obrigação."""
import re
from datetime import date

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None

RE_CNPJ = re.compile(r"\b(\d{2})\.?(\d{3})\.?(\d{3})/?(\d{4})-?(\d{2})\b")
RE_CPF = re.compile(r"\b(\d{3})\.(\d{3})\.(\d{3})-(\d{2})\b")
RE_DATA = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
RE_VALOR = re.compile(r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})\b")
RE_PERIODO = re.compile(r"\b(?:(\d{2})/)?(\d{2})/(\d{4})\b")

CODIGOS_DARF = {
    "irrf": ["0561", "0588", "1708", "3208"],
    "pis-cofins": ["8109", "2172", "6912", "5856"],
    "irpj-csll": ["2089", "2372"],
    "irpj-est": ["2362", "2484"],
}


def texto_pdf(caminho):
    if PdfReader is None:
        raise RuntimeError("Biblioteca de PDF não disponível")
    r = PdfReader(caminho)
    return "\n".join((p.extract_text() or "") for p in r.pages)


def _num(v):
    return float(v.replace(".", "").replace(",", "."))


def _norm(t):
    t = t.upper()
    for a, b in (("Á", "A"), ("À", "A"), ("Ã", "A"), ("Â", "A"), ("É", "E"), ("Ê", "E"), ("Í", "I"),
                 ("Ó", "O"), ("Õ", "O"), ("Ô", "O"), ("Ú", "U"), ("Ç", "C")):
        t = t.replace(a, b)
    return t


def identificar_tipo(texto):
    t = _norm(texto)
    if "DOCUMENTO DE ARRECADACAO DO SIMPLES NACIONAL" in t or "DAS " in t[:400]:
        if "MEI" in t or "SIMEI" in t or "MICROEMPREENDEDOR" in t:
            return "das-mei"
        return "das"
    if "FGTS DIGITAL" in t or "GUIA DO FGTS" in t or "GFD" in t:
        return "fgts"
    if "DARF" in t or "DOCUMENTO DE ARRECADACAO DE RECEITAS FEDERAIS" in t:
        if "DCTFWEB" in t or "CONTRIBUICOES PREVIDENCIARIAS" in t or "CONTRIBUICAO PREVIDENCIARIA" in t:
            return "inss"
        for tipo, cods in CODIGOS_DARF.items():
            for c in cods:
                if re.search(r"\b" + c + r"\b", t):
                    return tipo
        return None
    if "GARE" in t or "DARE" in t or "ICMS" in t:
        return "icms"
    if "ISSQN" in t or re.search(r"\bISS\b", t):
        return "iss"
    return None


def _apos(texto, chaves, padrao, janela=160):
    """Primeiro valor do padrão que aparece logo depois de uma das palavras-chave."""
    t = _norm(texto)
    for ch in chaves:
        for m in re.finditer(ch, t):
            trecho = texto[m.end(): m.end() + janela]
            r = padrao.search(trecho)
            if r:
                return r
    return None


def extrair(texto):
    """Devolve dict com cnpj, tipo, valor, vencimento (ISO) e período (AAAA-MM)."""
    info = {"cnpj": None, "tipo": identificar_tipo(texto), "valor": None, "vencimento": None, "periodo": None}
    m = RE_CNPJ.search(texto)
    if m:
        info["cnpj"] = "".join(m.groups())
    else:
        m = RE_CPF.search(texto)
        if m:
            info["cnpj"] = "".join(m.groups())

    d = _apos(texto, [r"PAGAR (ESTE DOCUMENTO )?ATE", r"DATA DE VENCIMENTO", r"VENCIMENTO", r"DATA LIMITE",
                      r"PAGAVEL ATE", r"VALIDO ATE"], RE_DATA)
    if d:
        info["vencimento"] = f"{d.group(3)}-{d.group(2)}-{d.group(1)}"

    v = _apos(texto, [r"VALOR TOTAL DO DOCUMENTO", r"VALOR TOTAL", r"TOTAL A RECOLHER", r"VALOR A RECOLHER",
                      r"VALOR DO DOCUMENTO", r"TOTAL"], RE_VALOR, janela=120)
    if v:
        info["valor"] = _num(v.group(1))
    else:
        valores = [_num(x) for x in RE_VALOR.findall(texto)]
        if valores:
            info["valor"] = max(valores)

    meses = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO",
             "NOVEMBRO", "DEZEMBRO"]
    pm = _apos(texto, [r"PERIODO DE APURACAO", r"COMPETENCIA", r"PA:", r"PERIODO"],
               re.compile(r"(" + "|".join(meses) + r")\s*(?:/|DE)?\s*(\d{4})", re.I), janela=80)
    p = _apos(texto, [r"PERIODO DE APURACAO", r"COMPETENCIA", r"PA:", r"PERIODO"], RE_PERIODO, janela=80)
    if pm and (not p or pm.start() <= p.start()):
        info["periodo"] = f"{pm.group(2)}-{meses.index(_norm(pm.group(1))) + 1:02d}"
    elif p:
        info["periodo"] = f"{p.group(3)}-{p.group(2)}"
    return info


def casar(info, clientes):
    """Acha o cliente pelo CNPJ completo; se não achar, pela raiz de 8 dígitos (filial)."""
    doc = info.get("cnpj")
    if not doc:
        return None
    for c in clientes:
        if (c.get("cnpj") or "") == doc:
            return c
    if len(doc) == 14:
        raiz = doc[:8]
        for c in clientes:
            if (c.get("cnpj") or "")[:8] == raiz and len(c.get("cnpj") or "") == 14:
                return c
    return None


def proximo_protocolo(comp, tarefas):
    """PRT-AAAAMM-NNNN: maior sequência já usada na competência + 1."""
    pref = "PRT-" + comp.replace("-", "") + "-"
    maior = 0
    for t in tarefas:
        for e in t.get("envios") or []:
            p = e.get("protocolo") or ""
            if p.startswith(pref):
                try:
                    maior = max(maior, int(p[len(pref):]))
                except ValueError:
                    pass
    return maior + 1, pref


def br(iso):
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}" if iso else ""


def moeda(v):
    if v is None:
        return ""
    s = f"{v:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def hoje_iso():
    return date.today().isoformat()
