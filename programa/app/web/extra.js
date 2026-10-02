// Telas do programa que não existiam no painel: enviar guias, conferir ciência, cobrar,
// importar clientes, configurar e-mail e pasta de dados.
const G = { linhas: [], lendo: false, enviando: false, confirmar: false, resultado: null, erro: null };
const CI = { rodando: false, ultimo: null };
const EM = { cfg: null, prov: {}, testando: false, msg: null, info: null };
let IMP = null; // prévia da importação de clientes

const lerArquivo = f => new Promise((ok, falha) => { const r = new FileReader(); r.onload = () => ok(r.result.split(",")[1]); r.onerror = falha; r.readAsDataURL(f); });
const valBR = v => v == null || v === "" ? "" : String(v).replace(".", ",");
const brVal = s => { s = String(s || "").trim(); if (!s) return null; s = s.replace(/[^\d,.-]/g, ""); if (s.includes(",")) s = s.replace(/\./g, "").replace(",", "."); const n = +s; return isNaN(n) ? null : n; };

// ---------------- Enviar guias ----------------
function gruposGuias() {
  const m = new Map();
  for (const l of G.linhas) {
    if (!l.incluir || !l.clienteId || !l.obrigId) continue;
    if (!m.has(l.clienteId)) m.set(l.clienteId, { clienteId: l.clienteId, itens: [] });
    m.get(l.clienteId).itens.push({ obrigId: l.obrigId, arquivo: l.arquivo, valor: l.valor, vencimento: l.vencimento || l.vencPrevisto || null });
  }
  return [...m.values()];
}
function viewGuias() {
  let html = `<header class="top"><div><h1>Enviar guias de ${compBR(S.comp)}</h1><p class="sub">Escolha os PDFs das guias. O programa identifica cliente, obrigação, valor e vencimento, e manda um e-mail por cliente com número de protocolo.</p></div>
  <div class="toolbar"><label class="f">Competência<select data-act="comp">${compOptions()}</select></label></div></header>`;
  html += `<div class="panel" style="padding:16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap">
    <input type="file" id="g-arqs" accept="application/pdf,.pdf" multiple>
    <button class="btn primary" data-act="g-ler" ${G.lendo ? "disabled" : ""}>${G.lendo ? "Lendo…" : "Ler guias"}</button>
    ${G.linhas.length ? `<button class="btn" data-act="g-limpar">Limpar lista</button>` : ""}
    <span class="hint">Os arquivos ficam guardados na pasta de dados, em guias/${S.comp}.</span></div>`;
  if (G.erro) html += `<div class="offline">${h(G.erro)}</div>`;
  if (G.resultado) {
    html += `<div class="panel" style="padding:14px 16px"><p class="sectionlabel">Resultado do envio</p><ul style="margin:0;padding-left:18px">${G.resultado.map(r => r.ok
      ? `<li><b>${h(r.cliente)}</b>: enviado para ${h((r.para || []).join(", "))} · <span class="mono">${h(r.protocolo)}</span></li>`
      : `<li style="color:var(--bad)"><b>${h(r.cliente || r.clienteId)}</b>: ${h(r.erro)} (envio interrompido)</li>`).join("")}</ul></div>`;
  }
  if (!G.linhas.length) return html + `<div class="panel empty"><h3>Nenhuma guia carregada</h3><p>Selecione os PDFs (DAS, DARF, FGTS, ICMS, ISS) e clique em <b>Ler guias</b>. Antes de enviar você confere tudo numa tabela.</p></div>`;
  const cliOpts = sel => `<option value="">— escolher —</option>` + [...S.clientes].sort((a, b) => a.nome.localeCompare(b.nome)).map(c => `<option value="${h(c.id)}" ${c.id === sel ? "selected" : ""}>${h(c.nome)}</option>`).join("");
  const obOpts = sel => `<option value="">— escolher —</option>` + [...S.obrig].filter(o => o.tipo === "guia" || o.id === sel).sort((a, b) => a.sigla.localeCompare(b.sigla)).map(o => `<option value="${h(o.id)}" ${o.id === sel ? "selected" : ""}>${h(o.sigla)}</option>`).join("");
  const rows = G.linhas.map((l, i) => `<tr>
    <td><input type="checkbox" data-act="g-campo" data-i="${i}" data-k="incluir" ${l.incluir ? "checked" : ""}></td>
    <td class="mono" style="max-width:220px;overflow:hidden;text-overflow:ellipsis" title="${h(l.arquivo)}">${h(l.arquivo)}</td>
    <td><select data-act="g-campo" data-i="${i}" data-k="clienteId" style="max-width:220px">${cliOpts(l.clienteId)}</select><div class="mono muted">${h(fmtCNPJ(l.cnpj))}</div></td>
    <td><select data-act="g-campo" data-i="${i}" data-k="obrigId">${obOpts(l.obrigId)}</select></td>
    <td><input type="date" value="${h(l.vencimento || "")}" data-act="g-campo" data-i="${i}" data-k="vencimento"></td>
    <td><input type="text" value="${h(valBR(l.valor))}" data-act="g-campo" data-i="${i}" data-k="valor" style="width:110px"></td>
    <td>${(l.alertas || []).length ? `<ul style="margin:0;padding-left:16px;color:var(--warn);font-size:12.5px">${l.alertas.map(a => `<li>${h(a)}</li>`).join("")}</ul>` : `<span class="pill st-concluida">OK</span>`}</td></tr>`).join("");
  const grupos = gruposGuias();
  const semEmail = grupos.filter(g => !((byId(S.clientes, g.clienteId) || {}).emails || []).length);
  html += `<div class="panel tablewrap"><table><thead><tr><th></th><th>Arquivo</th><th>Cliente</th><th>Obrigação</th><th>Vencimento</th><th>Valor (R$)</th><th>Conferência</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  const resumo = grupos.map(g => { const c = byId(S.clientes, g.clienteId) || {}; return `<li><b>${h(c.nome || g.clienteId)}</b> → ${h((c.emails || []).join(", ") || "SEM E-MAIL")} · ${g.itens.map(i => h((byId(S.obrig, i.obrigId) || { sigla: i.obrigId }).sigla)).join(", ")}</li>`; }).join("");
  html += `<div class="panel" style="padding:14px 16px;display:flex;flex-direction:column;gap:10px"><p class="sectionlabel" style="margin:0">Serão enviados ${grupos.length} e-mail(s)</p>
    ${grupos.length ? `<ul style="margin:0;padding-left:18px">${resumo}</ul>` : `<p class="muted" style="margin:0">Marque as guias e escolha cliente e obrigação.</p>`}
    ${semEmail.length ? `<div class="offline">Cadastre o e-mail de ${semEmail.length} cliente(s) antes de enviar.</div>` : ""}
    <div style="display:flex;gap:8px;flex-wrap:wrap">${G.confirmar
      ? `<span style="align-self:center">Confirma o envio de ${grupos.length} e-mail(s) agora?</span><button class="btn primary" data-act="g-enviar-sim" ${G.enviando ? "disabled" : ""}>${G.enviando ? "Enviando…" : "Sim, enviar"}</button><button class="btn" data-act="g-enviar-nao">Voltar</button>`
      : `<button class="btn primary" data-act="g-enviar" ${!grupos.length || semEmail.length ? "disabled" : ""}>Enviar ${grupos.length} e-mail(s)</button>`}</div></div>`;
  return html;
}

// ---------------- Protocolos: conferir respostas ----------------
function blocoCiencia() {
  let s = `<div class="panel" style="padding:12px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap">
    <button class="btn primary" data-act="ci-conferir" ${CI.rodando ? "disabled" : ""}>${CI.rodando ? "Lendo a caixa de entrada…" : "Conferir respostas dos clientes"}</button>
    <span class="hint">Lê a Caixa de Entrada e registra a ciência de quem respondeu ao e-mail do protocolo.</span></div>`;
  if (CI.ultimo) {
    const u = CI.ultimo;
    s += `<div class="panel" style="padding:12px 16px">${u.erro ? `<div class="offline">${h(u.erro)}</div>` : `<p style="margin:0 0 6px"><b>${u.novos.length}</b> nova(s) ciência(s). ${u.aguardando} protocolo(s) ainda aguardando.</p>
      ${u.novos.length ? `<ul style="margin:0;padding-left:18px">${u.novos.map(n => `<li><span class="mono">${h(n.protocolo)}</span> · ${h(n.cliente || "")} · ${h(n.de)}${n.verificar ? ` <span class="pill st-semresp">verificar resposta</span>` : ""}<div class="muted">${h(n.resposta)}</div></li>`).join("")}</ul>` : ""}`}</div>`;
  }
  return s;
}

// ---------------- Configurações: e-mail e pasta ----------------
function blocoEmail() {
  if (!EM.cfg) { carregaEmail(); return `<div class="panel" style="padding:18px">Carregando configuração de e-mail…</div>`; }
  const c = EM.cfg, p = EM.prov;
  const opt = Object.entries(p).map(([k, v]) => `<option value="${k}" ${c.provedor === k ? "selected" : ""}>${h(v.nome)}</option>`).join("");
  const dica = (p[c.provedor] || {}).dica || "";
  return `<form class="panel cfg" id="em-form" data-act="em-salvar" style="margin-top:4px">
  <div class="full"><h2 style="font-family:var(--f-display);font-size:19px;margin:0">E-mail de envio das guias</h2><p class="hint" style="margin:4px 0 0">Fica guardado só neste computador. A senha é protegida pelo Windows.</p></div>
  <label class="f">Provedor<select id="em-prov" data-act="em-prov"><option value="">— escolher —</option>${opt}</select></label>
  <label class="f">E-mail remetente<input type="email" id="em-rem" value="${h(c.remetente || "")}" placeholder="guias@escritorio.com.br"></label>
  <label class="f">Nome que aparece<input type="text" id="em-nome" value="${h(c.nome_remetente || "")}" placeholder="Escritório Contábil"></label>
  <label class="f">Usuário (se diferente do e-mail)<input type="text" id="em-user" value="${h(c.usuario || "")}"></label>
  <label class="f">Senha${c.tem_senha ? " (já salva; preencha só para trocar)" : ""}<input type="password" id="em-senha" autocomplete="new-password"></label>
  <label class="f">Cópia oculta de cada envio (opcional)<input type="email" id="em-bcc" value="${h(c.copia_para || "")}"></label>
  <label class="f">Servidor SMTP (envio)<input type="text" id="em-smtp" value="${h(c.smtp || "")}"></label>
  <label class="f">Porta / segurança<span style="display:flex;gap:6px"><input type="number" id="em-sp" value="${h(c.smtp_porta || 465)}" style="width:90px"><select id="em-sseg"><option value="ssl" ${c.smtp_seg !== "starttls" ? "selected" : ""}>SSL</option><option value="starttls" ${c.smtp_seg === "starttls" ? "selected" : ""}>STARTTLS</option></select></span></label>
  <label class="f">Servidor IMAP (leitura das respostas)<input type="text" id="em-imap" value="${h(c.imap || "")}"></label>
  <label class="f">Porta IMAP<input type="number" id="em-ip" value="${h(c.imap_porta || 993)}"></label>
  ${dica ? `<p class="full hint" style="margin:0">${h(dica)}</p>` : ""}
  ${EM.msg ? `<div class="full ${EM.msg.ok ? "" : "offline"}" style="${EM.msg.ok ? "color:var(--ok);font-weight:600" : ""}">${h(EM.msg.texto)}</div>` : ""}
  <div class="full" style="display:flex;gap:8px"><button class="btn primary" type="submit">Salvar e-mail</button><button class="btn" type="button" data-act="em-testar" ${EM.testando ? "disabled" : ""}>${EM.testando ? "Testando…" : "Testar conexão"}</button></div></form>
  ${blocoPasta()}`;
}
function blocoPasta() {
  const i = EM.info || {};
  return `<div class="panel cfg" style="margin-top:4px"><div class="full"><h2 style="font-family:var(--f-display);font-size:19px;margin:0">Pasta de dados</h2>
  <p class="hint" style="margin:4px 0 0">Para a equipe trabalhar junta, todos apontam para a mesma pasta da rede (ex.: \\\\SERVIDOR\\Contabil\\CentralObrigacoes).</p></div>
  <label class="f full">Pasta atual<input type="text" id="pd-pasta" value="${h(i.pastaDados || "")}"></label>
  <div class="full" style="display:flex;gap:8px;align-items:center"><button class="btn" data-act="pd-salvar">Usar esta pasta</button><span class="hint">Programa versão ${h(i.versao || "")}</span></div></div>`;
}
async function carregaEmail() {
  try { const j = await apiLocal("/api/email/config"); EM.cfg = j.config; EM.prov = j.provedores; EM.info = await apiLocal("/api/info"); }
  catch (e) { EM.cfg = {}; EM.msg = { ok: false, texto: e.message }; }
  if (S.view === "config") render();
}

// ---------------- Importar clientes ----------------
function modalImport() {
  const el = document.getElementById("overlay2"); if (!IMP) { el.innerHTML = ""; return; }
  const ok = IMP.clientes.filter(c => !c.invalido && !c.repetido);
  const reg = {}; ok.forEach(c => reg[c.regime || "(sem regime)"] = (reg[c.regime || "(sem regime)"] || 0) + 1);
  const semEmail = ok.filter(c => !c.emails.length).length, existem = ok.filter(c => c.existe).length;
  el.innerHTML = `<div class="scrim" data-act="imp-fechar"></div><div class="modal" role="dialog" aria-label="Importar clientes">
  <header><h2>Importar clientes</h2><button class="x" data-act="imp-fechar" aria-label="Fechar">×</button></header>
  <div class="body"><div class="full">
  <p><b>${ok.length}</b> cliente(s) válidos: ${Object.entries(reg).map(([k, v]) => `${h(k)} ${v}`).join(" · ")}.</p>
  <p class="muted">${semEmail} sem e-mail · ${existem} já cadastrados (só completo o que estiver vazio) · ${IMP.clientes.length - ok.length} ignorados (CNPJ inválido ou repetido).</p>
  <div class="tablewrap" style="max-height:320px;overflow:auto"><table><thead><tr><th>Nome</th><th>CNPJ/CPF</th><th>Regime</th><th>E-mails</th><th>Obrig.</th><th></th></tr></thead><tbody>
  ${IMP.clientes.map(c => `<tr><td>${h(c.nome)}</td><td class="mono">${h(fmtCNPJ(c.cnpj))}</td><td>${h(c.regime || "—")}</td><td class="muted">${h(c.emails.join(", "))}</td><td class="mono">${c.obrigacoes.length}</td><td>${c.invalido ? `<span class="pill st-atrasada">CNPJ inválido</span>` : c.repetido ? `<span class="pill st-dispensada">repetido</span>` : c.existe ? `<span class="pill st-andamento">já existe</span>` : ""}</td></tr>`).join("")}
  </tbody></table></div>
  <p class="hint">As obrigações de cada cliente são marcadas pelo regime. Você pode ajustar depois em Clientes.</p></div></div>
  <footer><span></span><span style="display:flex;gap:8px"><button class="btn" data-act="imp-fechar">Cancelar</button><button class="btn primary" data-act="imp-gravar" ${!ok.length ? "disabled" : ""}>Importar ${ok.length}</button></span></footer></div>`;
}

// ---------------- encaixe nas telas do painel ----------------
const _viewCfg = viewCfg; viewCfg = function () { return _viewCfg() + blocoEmail(); };
const _viewProt = viewProtocolos; viewProtocolos = function () {
  const s = _viewProt(); const i = s.indexOf("</header>") + 9; return s.slice(0, i) + blocoCiencia() + s.slice(i);
};
const _viewCli = viewClientes; viewClientes = function () {
  return _viewCli().replace(`<button class="btn primary" data-act="cli-new">Novo cliente</button></div></header>`,
    `<label class="btn" style="cursor:pointer">Importar planilha<input type="file" id="imp-arq" accept=".xlsx,.xlsm,.csv" hidden></label><button class="btn primary" data-act="cli-new">Novo cliente</button></div></header>`);
};
const _drawerProto = drawerProto; drawerProto = function (o) {
  const t = byId(S.tarefas, o.t); const e = t && (t.envios || [])[o.i];
  let s = _drawerProto(o);
  if (e && e.status !== "ciente") s = s.replace(`<footer><button class="btn" data-act="close">Fechar</button>`, `<footer><button class="btn" data-act="close">Fechar</button><button class="btn" data-act="cobrar" data-t="${h(o.t)}" data-i="${o.i}">Cobrar cliente por e-mail</button>`);
  return s;
};

document.addEventListener("change", async ev => {
  const el = ev.target;
  if (el.id === "imp-arq" && el.files[0]) {
    const f = el.files[0];
    try { IMP = await apiLocal("/api/clientes/analisar", { nome: f.name, b64: await lerArquivo(f) }); modalImport(); }
    catch (e) { toast(e.message); }
    el.value = "";
  }
  if (el.dataset.act === "g-campo") {
    const l = G.linhas[+el.dataset.i], k = el.dataset.k;
    l[k] = k === "incluir" ? el.checked : k === "valor" ? brVal(el.value) : el.value;
    G.confirmar = false; G.resultado = null; render();
  }
  if (el.dataset.act === "em-prov") {
    const p = EM.prov[el.value]; if (!p) return;
    Object.assign(EM.cfg, lerEmailForm(), { provedor: el.value, smtp: p.smtp, smtp_porta: p.smtp_porta, smtp_seg: p.smtp_seg, imap: p.imap, imap_porta: p.imap_porta });
    S.cfgRendered = false; render();
  }
});
function lerEmailForm() {
  const v = id => (document.getElementById(id) || {}).value;
  return { provedor: v("em-prov"), remetente: (v("em-rem") || "").trim(), nome_remetente: v("em-nome"), usuario: (v("em-user") || "").trim(), senha: v("em-senha"),
    copia_para: (v("em-bcc") || "").trim(), smtp: (v("em-smtp") || "").trim(), smtp_porta: +v("em-sp") || 465, smtp_seg: v("em-sseg"), imap: (v("em-imap") || "").trim(), imap_porta: +v("em-ip") || 993 };
}
document.addEventListener("submit", async ev => {
  if (ev.target.dataset.act !== "em-salvar") return;
  ev.preventDefault(); ev.stopImmediatePropagation();
  const d = lerEmailForm();
  try { await apiLocal("/api/email/config", d); EM.cfg = null; EM.msg = { ok: true, texto: "E-mail salvo. Use “Testar conexão” para conferir." }; await carregaEmail(); }
  catch (e) { EM.msg = { ok: false, texto: e.message }; render(); }
}, true);

document.addEventListener("click", async ev => {
  const el = ev.target.closest("[data-act]"); if (!el) return;
  const a = el.dataset.act;
  if (a === "g-ler") {
    const arqs = [...(document.getElementById("g-arqs").files || [])];
    if (!arqs.length) { toast("Selecione os PDFs das guias."); return; }
    G.lendo = true; G.erro = null; G.resultado = null; render();
    try {
      const arquivos = []; for (const f of arqs) arquivos.push({ nome: f.name, b64: await lerArquivo(f) });
      const j = await apiLocal("/api/guias/analisar", { comp: S.comp, arquivos });
      const ja = new Set(G.linhas.map(l => l.arquivo));
      for (const l of j.guias) { l.incluir = !!(l.clienteId && l.obrigId) && !(l.alertas || []).some(x => /já foi enviada|não enviar/.test(x)); if (ja.has(l.arquivo)) G.linhas = G.linhas.filter(x => x.arquivo !== l.arquivo); G.linhas.push(l); }
    } catch (e) { G.erro = e.message; }
    G.lendo = false; render();
  }
  else if (a === "g-limpar") { G.linhas = []; G.resultado = null; G.confirmar = false; render(); }
  else if (a === "g-enviar") { G.confirmar = true; render(); }
  else if (a === "g-enviar-nao") { G.confirmar = false; render(); }
  else if (a === "g-enviar-sim") {
    G.enviando = true; render();
    try {
      const j = await apiLocal("/api/guias/enviar", { comp: S.comp, grupos: gruposGuias() });
      G.resultado = j.resultados;
      const ok = new Set(j.resultados.filter(r => r.ok).map(r => r.cliente));
      G.linhas = G.linhas.filter(l => !(l.incluir && ok.has((byId(S.clientes, l.clienteId) || {}).nome)));
    } catch (e) { G.erro = e.message; }
    G.enviando = false; G.confirmar = false; atualizarAgora(); render();
  }
  else if (a === "ci-conferir") {
    CI.rodando = true; render();
    try { CI.ultimo = await apiLocal("/api/ciencia/conferir", {}); } catch (e) { CI.ultimo = { erro: e.message }; }
    CI.rodando = false; atualizarAgora(); render();
  }
  else if (a === "cobrar") {
    el.disabled = true; el.textContent = "Enviando…";
    try { await apiLocal("/api/cobrar", { tarefaId: el.dataset.t, idx: +el.dataset.i }); toast("Cobrança enviada"); atualizarAgora(); }
    catch (e) { toast(e.message); el.disabled = false; el.textContent = "Cobrar cliente por e-mail"; }
  }
  else if (a === "em-testar") {
    const form = lerEmailForm(); EM.testando = true; EM.msg = null; Object.assign(EM.cfg, form); S.cfgRendered = false; render();
    try { await apiLocal("/api/email/config", form); if (form.senha) EM.cfg.tem_senha = true; const j = await apiLocal("/api/email/testar", {}); EM.msg = j.ok ? { ok: true, texto: "Conexão OK: envio e leitura funcionando." } : { ok: false, texto: j.erros.join(" | ") }; }
    catch (e) { EM.msg = { ok: false, texto: e.message }; }
    EM.testando = false; S.cfgRendered = false; render();
  }
  else if (a === "pd-salvar") {
    const pasta = document.getElementById("pd-pasta").value;
    try { await apiLocal("/api/pasta-dados", { pasta }); toast("Pasta salva. Feche e abra o programa para usar a nova pasta."); }
    catch (e) { toast(e.message); }
  }
  else if (a === "imp-fechar") { IMP = null; modalImport(); }
  else if (a === "imp-gravar") {
    try { const j = await apiLocal("/api/clientes/importar", { clientes: IMP.clientes }); toast(`${j.gravados} cliente(s) importados`); IMP = null; modalImport(); atualizarAgora(); }
    catch (e) { toast(e.message); }
  }
});
