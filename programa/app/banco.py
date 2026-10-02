"""Banco de documentos em SQLite (coleção/id -> JSON), compatível com o painel.

Cada gravação incrementa um contador de revisão. A tela consulta esse
contador a cada poucos segundos e recarrega o que mudou, assim várias
máquinas usando a mesma pasta da rede veem as alterações umas das outras.
"""
import json
import os
import sqlite3
import threading
import time
import uuid

_lock = threading.RLock()


def _merge(base, novo):
    """update(): mescla objetos aninhados; listas e valores simples substituem."""
    for k, v in novo.items():
        if isinstance(v, dict) and v.get("__delete__") is True:
            base.pop(k, None)
        elif isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


class Banco:
    def __init__(self, pasta):
        os.makedirs(pasta, exist_ok=True)
        self.caminho = os.path.join(pasta, "central-obrigacoes.db")
        self._con = sqlite3.connect(self.caminho, check_same_thread=False, timeout=30)
        self._con.execute("PRAGMA busy_timeout=30000")
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS docs (col TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL,"
            " rev INTEGER NOT NULL, PRIMARY KEY (col, id))")
        self._con.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
        self._con.execute("CREATE INDEX IF NOT EXISTS docs_rev ON docs(rev)")
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS apagados (col TEXT NOT NULL, id TEXT NOT NULL, rev INTEGER NOT NULL)")
        self._con.commit()

    # ---------- revisão ----------
    def rev(self):
        with _lock:
            r = self._con.execute("SELECT v FROM meta WHERE k='rev'").fetchone()
            return int(r[0]) if r else 0

    def _bump(self):
        r = self.rev() + 1
        self._con.execute("INSERT OR REPLACE INTO meta (k, v) VALUES ('rev', ?)", (str(r),))
        return r

    # ---------- leitura ----------
    def listar(self, col):
        with _lock:
            rows = self._con.execute("SELECT id, data FROM docs WHERE col=? ORDER BY id", (col,)).fetchall()
        return [{"id": i, **json.loads(d)} for i, d in rows]

    def obter(self, col, id_):
        with _lock:
            r = self._con.execute("SELECT data FROM docs WHERE col=? AND id=?", (col, id_)).fetchone()
        return json.loads(r[0]) if r else None

    def colecoes_alteradas(self, desde):
        with _lock:
            a = {c for (c,) in self._con.execute("SELECT DISTINCT col FROM docs WHERE rev>?", (desde,))}
            b = {c for (c,) in self._con.execute("SELECT DISTINCT col FROM apagados WHERE rev>?", (desde,))}
        return sorted(a | b)

    # ---------- escrita ----------
    def set(self, col, id_, data):
        data = {k: v for k, v in (data or {}).items() if k != "id"}
        with _lock:
            r = self._bump()
            self._con.execute("INSERT OR REPLACE INTO docs (col, id, data, rev) VALUES (?,?,?,?)",
                              (col, id_, json.dumps(data, ensure_ascii=False), r))
            self._con.commit()
        return data

    def update(self, col, id_, data):
        with _lock:
            atual = self.obter(col, id_)
            if atual is None:
                raise KeyError(f"{col}/{id_} não existe")
            novo = _merge(atual, {k: v for k, v in data.items() if k != "id"})
            return self.set(col, id_, novo)

    def delete(self, col, id_):
        with _lock:
            r = self._bump()
            self._con.execute("DELETE FROM docs WHERE col=? AND id=?", (col, id_))
            self._con.execute("INSERT INTO apagados (col, id, rev) VALUES (?,?,?)", (col, id_, r))
            self._con.commit()

    def lote(self, escritas):
        """escritas: [{op: set|update|delete, col, id, data}] numa transação só."""
        with _lock:
            for w in escritas:
                op, col, id_ = w["op"], w["col"], w["id"]
                if op == "set":
                    self.set(col, id_, w.get("data") or {})
                elif op == "update":
                    self.update(col, id_, w.get("data") or {})
                elif op == "delete":
                    self.delete(col, id_)

    @staticmethod
    def novo_id():
        return uuid.uuid4().hex[:20]

    def vazio(self):
        with _lock:
            return self._con.execute("SELECT COUNT(*) FROM docs").fetchone()[0] == 0


def semear(banco, pasta_catalogo):
    """Grava o catálogo inicial (obrigações, processos, configurações) num banco novo."""
    if not banco.vazio():
        return False
    for col, arq in (("obrigacoes", "obrigacoes.json"), ("processos", "processos.json")):
        with open(os.path.join(pasta_catalogo, arq), encoding="utf-8") as f:
            for id_, d in json.load(f).items():
                banco.set(col, id_, d)
    with open(os.path.join(pasta_catalogo, "config.json"), encoding="utf-8") as f:
        banco.set("config", "escritorio", json.load(f))
    return True


def agora_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S")
