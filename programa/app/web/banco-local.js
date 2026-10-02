// Adaptador: oferece ao painel a mesma interface de banco (window.claude.use("db")),
// gravando no servidor local do programa e acompanhando mudanças por consulta periódica.
(() => {
  const api = async (url, corpo) => {
    const r = await fetch(url, corpo === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) });
    let j = null; try { j = await r.json(); } catch (e) { }
    if (!r.ok) { const err = new Error((j && j.erro) || ("HTTP " + r.status)); err.code = r.status === 404 ? "not_found" : "internal"; throw err; }
    return j;
  };
  window.apiLocal = api;
  const subsCol = new Map();  // nome -> [ {cb, err} ]
  const subsDoc = new Map();  // "col/id" -> [ {cb, err} ]
  let rev = -1, timer = null, rodando = false;

  const snapCol = arr => ({ docs: arr.map(d => { const { id, ...resto } = d; return { id, data: () => resto }; }) });
  async function carregaCol(nome) {
    const lista = subsCol.get(nome) || [];
    try { const arr = await api("/api/col/" + nome); lista.forEach(s => s.cb(snapCol(arr))); }
    catch (e) { lista.forEach(s => s.err && s.err(e)); }
  }
  async function carregaDoc(chave) {
    const lista = subsDoc.get(chave) || [];
    try { const j = await api("/api/doc/" + chave); lista.forEach(s => s.cb({ exists: j.existe, data: () => j.data || {} })); }
    catch (e) { lista.forEach(s => s.err && s.err(e)); }
  }
  async function verificar() {
    if (rodando) return; rodando = true;
    try {
      const j = await api("/api/alteradas?desde=" + Math.max(rev, 0));
      if (j.rev !== rev) {
        const primeira = rev < 0; rev = j.rev;
        const cols = primeira ? null : new Set(j.colecoes);
        for (const nome of subsCol.keys()) if (!cols || cols.has(nome)) await carregaCol(nome);
        for (const chave of subsDoc.keys()) if (!cols || cols.has(chave.split("/")[0])) await carregaDoc(chave);
      }
      document.body.classList.remove("sem-conexao");
    } catch (e) { document.body.classList.add("sem-conexao"); }
    finally { rodando = false; }
  }
  function agendar() { clearInterval(timer); timer = setInterval(verificar, 2500); }
  window.atualizarAgora = verificar;

  const novoId = () => Array.from(crypto.getRandomValues(new Uint8Array(10)), b => b.toString(16).padStart(2, "0")).join("");
  const escrever = async (col, id, op, data) => { await api(`/api/doc/${col}/${encodeURIComponent(id)}`, { op, data }); verificar(); };

  const db = {
    collection(nome) {
      return {
        onSnapshot(cb, err) {
          if (!subsCol.has(nome)) subsCol.set(nome, []);
          subsCol.get(nome).push({ cb, err }); carregaCol(nome); return () => { };
        },
        doc(id) { id = id || novoId(); return db.doc(nome + "/" + id); }
      };
    },
    doc(caminho) {
      const [col, id] = caminho.split("/");
      return {
        id,
        onSnapshot(cb, err) {
          if (!subsDoc.has(caminho)) subsDoc.set(caminho, []);
          subsDoc.get(caminho).push({ cb, err }); carregaDoc(caminho); return () => { };
        },
        set: data => escrever(col, id, "set", data),
        update: data => escrever(col, id, "update", data),
        delete: () => escrever(col, id, "delete")
      };
    }
  };
  window.claude = { use: async () => { agendar(); setTimeout(verificar, 50); return db; } };
})();
