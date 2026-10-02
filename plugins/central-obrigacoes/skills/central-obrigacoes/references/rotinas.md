# Rotinas da Central de Obrigações

### 1. Importar ou cadastrar clientes

1. Leia a planilha do usuário (xlsx/csv) e identifique nome, CNPJ/CPF, regime, e-mail(s), responsável.
2. Leia `obrigacoes` (`ArtifactData list`). Para cada cliente, sugira as obrigações cujo `regimes[]` contém o regime dele.
3. Mostre ao usuário um resumo (quantos clientes por regime, quem ficou sem e-mail, CNPJs repetidos) e confirme antes de gravar.
4. Grave em lotes de 50 com `ArtifactData batch`, id = CNPJ só com dígitos (evita duplicar ao reimportar; use `update` quando já existir para não apagar ajustes feitos no painel).

### 2. Gerar a agenda da competência

O caminho normal é o botão **Gerar tarefas** no painel. Pela skill (útil para muitas competências ou em rotina agendada):
1. `ArtifactData list` de `clientes`, `obrigacoes`, `processos`, `config/escritorio` e das `tarefas` da competência (`ArtifactData query` com `where: [["competencia","==","AAAA-MM"]]`).
2. Para cada cliente ativo e cada obrigação dele que se aplica: `itens[obId] = {venc, status: "pendente", resp: cliente.resp, etapas: [{n, ok: false}...]}` com as etapas do processo da obrigação.
3. Documento novo: `set` com `{competencia, clienteId, clienteNome, criadoEm, itens, envios: []}`. Documento existente: `update` com `{itens: {só os que faltam}}`. Nunca sobrescreva itens que já existem.
4. Informe quantas tarefas criou e as datas de vencimento mais próximas.

### 3. Radar de prazos e lembretes

1. Leia `tarefas` das duas últimas competências e da atual, mais `obrigacoes` e `clientes`.
2. Monte três grupos: **Atrasadas** (aberta e `venc` < hoje), **Vencem hoje**, **No prazo de lembrete** (aberta e `venc` ≤ hoje + `lembrete` da obrigação).
3. Agrupe por responsável; para cada linha, cliente, sigla, vencimento (dia da semana e data) e a próxima etapa não concluída.
4. Responda em uma tabela curta no chat. Se o usuário pedir para avisar a equipe, rascunhe o e-mail por responsável e envie pelo Gmail só depois de ele confirmar os destinatários.
5. Esta rotina serve bem como tarefa agendada (dias úteis às 8h): no modo agendado, só leia e resuma, sem gravar nem enviar nada.

### 4. Enviar guias com protocolo (Gmail)

Entrada: uma pasta com os PDFs das guias (pasta conectada do computador ou arquivos anexados) e a competência.

1. **Ler as guias.** Traga os PDFs para o espaço de trabalho (`device_stage_files` ou uploads) e extraia o texto com `pdftotext -layout`. De cada guia tire: CNPJ/CPF, tipo, valor total, vencimento, período de apuração. Identificação do tipo:
   - "Documento de Arrecadação do Simples Nacional" → `das` (ou `das-mei` se o texto citar MEI/SIMEI)
   - DARF emitido pela DCTFWeb (texto "DCTFWeb" ou "Contribuições Previdenciárias") → `inss`
   - DARF código 0561/0588/1708/3208 → `irrf`; 8109/2172/6912/5856 → `pis-cofins`; 2089/2372 → `irpj-csll`; 2362/2484 → `irpj-est`
   - "FGTS Digital" / "GFD" → `fgts`; GARE/DARE/"ICMS" → `icms`; "ISS"/"ISSQN" → `iss`
   - Se não for possível identificar, marque "não identificado" e pergunte.
2. **Casar com a agenda.** Cliente pelo CNPJ (só dígitos, compare também a raiz de 8 dígitos para filiais); item pelo tipo na tarefa `AAAA-MM_{clienteId}`. Aponte diferenças: vencimento da guia diferente do previsto, cliente sem e-mail, guia sem tarefa, obrigação com `enviaCliente: false`.
3. **Conferência antes de enviar.** Mostre uma tabela: cliente, e-mails, guias (sigla, vencimento, valor), protocolo que será usado. Envie somente depois que o usuário confirmar. Um e-mail por cliente com todas as guias dele na competência.
4. **Protocolo.** Formato `PRT-AAAAMM-NNNN` (competência + sequência de 4 dígitos). Calcule a próxima sequência lendo todos os `envios` da competência e somando 1 ao maior número. Nunca reutilize um número.
5. **Montar o e-mail** a partir de `config/escritorio`: substitua `{cliente}`, `{cnpj}`, `{competencia}` (MM/AAAA), `{protocolo}`, `{escritorio}`; `{guias}` vira uma lista "SIGLA – nome – vence DD/MM/AAAA – R$ valor". Mande em `htmlBody` (parágrafos `<p>`, lista `<ul>`), com a assinatura no fim e o protocolo também no assunto.
6. **Enviar** com `mcp__Gmail__send_message`, anexos em `attachments` (`content` em base64, `filename` claro como `DAS_09-2026_NOMECLIENTE.pdf`, `mimeType: application/pdf`). Gere o base64 com `base64 -w0 arquivo.pdf` e copie exatamente. Se um PDF passar de ~150 KB, reduza antes (`gs -sDEVICE=pdfwrite -dPDFSETTINGS=/ebook`) e confira que o texto continua legível. Envie um cliente por vez e pare no primeiro erro.
7. **Registrar no painel** logo após cada envio que deu certo: leia a tarefa, acrescente ao `envios` o objeto com `protocolo`, `itens`, `para`, `assunto`, `anexos`, `enviadoEm` (agora, fuso America/Sao_Paulo), `threadId` e `messageId` retornados pelo Gmail, `status: "aguardando"`; nos itens enviados grave `status: "enviada"`, `valor`, `arquivo` e marque como feita a etapa "Enviar ao cliente" (`ok: true, em: hoje`).
8. Termine com: quantos e-mails saíram, protocolos gerados e o que ficou pendente.

### 5. Conferir ciência (recibo de leitura por resposta)

1. Leia as tarefas com `envios` em `status: "aguardando"`.
2. Para cada envio, `mcp__Gmail__get_thread` com o `threadId` e `messageFormat: "PLAIN_TEXT"`. Considere ciência a primeira mensagem **posterior ao envio** vinda de um remetente que não seja o próprio escritório (o endereço de entrega ou outro do mesmo domínio do cliente). Sem `threadId`, procure com `search_threads` pelo número do protocolo.
3. Grave no envio: `status: "ciente"`, `cienteEm` (data e hora da resposta), `cienteDe` (e-mail de quem respondeu), `cienteVia: "Resposta ao e-mail"`, `resposta` (texto novo da resposta, sem o histórico citado, até 400 caracteres). Os itens do envio que estão `enviada` passam para `ciente`.
4. Se a resposta traz dúvida ou problema (valor errado, "não recebi o anexo", pedido de reenvio, parcelamento), registre a ciência mesmo assim e liste esses casos para o usuário tratar.
5. Relate: novos cientes, quem segue aguardando e há quantos dias.

### 6. Cobrar quem não respondeu

1. Envios `aguardando` com mais de `diasCobranca` dias corridos desde `enviadoEm`, e cujas guias ainda não venceram (ou venceram há pouco).
2. Mostre a lista e peça confirmação.
3. Responda na mesma conversa (`send_message` com `replyThreadId`) um lembrete curto citando protocolo, guias e vencimento, pedindo a confirmação por resposta.
4. Acrescente a data em `cobrancas[]` do envio.

### 7. Relatórios e arquivamento

- **Relatório de protocolos** de um cliente ou período: planilha (skill xlsx) com protocolo, competência, guias, valores, vencimento, envio, ciência, quem confirmou e trecho da resposta. Serve como comprovante de entrega.
- **Arquivar**: quando o banco passar de ~20 mil documentos ou o usuário pedir, exporte as tarefas de competências com mais de 12 meses para uma planilha e, só com confirmação, apague esses documentos.
