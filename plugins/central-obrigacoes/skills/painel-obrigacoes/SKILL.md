---
name: painel-obrigacoes
description: Instala, conecta ou atualiza o painel on-line da Central de Obrigações. Use para "instalar a central de obrigações", "criar meu painel", "conectar ao painel do escritório", "atualizar o painel", "qual a versão do painel", ou quando a skill central-obrigacoes não encontrar painel.
---

# Painel da Central de Obrigações

Cada escritório tem **um painel próprio** (artifact com banco de dados). Os dados de um escritório nunca vão para o painel de outro. Membros da mesma equipe usam o mesmo painel, compartilhado pelo dono com acesso de edição.

Arquivos desta skill (caminhos relativos à pasta base desta skill, informada ao carregá-la):

- `assets/painel.html`: modelo do painel. A versão está em `<meta name="central-obrigacoes-versao" content="X.Y.Z">` e na constante `PAINEL_VERSAO`.
- `assets/catalogo/obrigacoes.json`, `processos.json`, `config.json`: catálogo inicial (objeto `{doc_id: dados}`), sem clientes.

## Localizar o painel do usuário

1. `Artifact` com `action: "list"`, `scope: "all"`, `limit: 50`. Considere os itens com título "Central de Obrigações".
2. Nenhum → ofereça **Instalar** (abaixo) ou pedir ao dono do escritório o link do painel.
3. Mais de um → pergunte qual usar (mostre dono e data de atualização). Nunca misture dados de dois painéis.
4. Se o usuário colar um link, use esse link.

## Instalar (escritório novo)

1. Pergunte o nome do escritório e os responsáveis (opcional).
2. Copie `assets/painel.html` para o scratchpad da sessão (o Artifact só publica arquivos do diretório de trabalho ou do scratchpad). Leia o arquivo inteiro antes de publicar.
3. Publique: `Artifact` `action: "publish"`, `file_path` = cópia, `icon: "calendar"`, `capabilities: {"db": {}}`, `description: "Agenda de obrigações acessórias e protocolos de entrega de guias."`. Guarde a URL retornada.
4. Grave o catálogo com `ArtifactData` `action: "batch"` (até 50 por lote, `op: "set"`, sem `if_version` porque os documentos são novos): cada entrada de `obrigacoes.json` em `obrigacoes/{id}`, de `processos.json` em `processos/{id}`, e `config.json` em `config/escritorio` com `nome` e `responsaveis` preenchidos.
5. Avise: os feriados vêm só nacionais (2026–2027); incluir estaduais e municipais em Configurações. ICMS, ISS, EFD ICMS/IPI e DeSTDA têm datas genéricas para ajustar ao estado e município.
6. Próximo passo sugerido: importar a carteira de clientes de uma planilha (skill central-obrigacoes).

## Conectar a equipe a um painel existente

O dono abre o painel, menu **Compartilhar**, e convida o colega por e-mail com permissão de **edição**. O colega cola o link numa conversa; a skill passa a encontrá-lo pela listagem `scope: "all"`. Se `ArtifactData` recusar gravação, o convite foi só de leitura: peça ao dono para mudar para edição.

## Atualizar o painel (nova versão do plugin)

Faça isto quando o usuário pedir, ou quando a skill central-obrigacoes notar que o painel está desatualizado.

1. Localize o painel e leia com `Artifact` `action: "read"`. Pegue a versão no `<meta name="central-obrigacoes-versao">` (sem a tag, trate como `0.0.0`).
2. Compare com a versão de `assets/painel.html`. Igual ou maior → informe que já está atualizado.
3. Menor → só o **dono** do painel (leitura indica "writer" e é dele) pode republicar. Se não for o dono, diga quem deve rodar a atualização.
4. Copie `assets/painel.html` para o scratchpad, leia inteiro e publique com `Artifact` `action: "publish"`, `file_path` = cópia e `url` = URL do painel. Não passe `capabilities` (mantém o banco) nem `icon`. Os dados do banco não são tocados.
5. Se houver conflito de versão (alguém publicou antes), releia e repita; nunca use `force`.
6. Se a nova versão trouxer obrigações novas no catálogo, grave **apenas** as que não existem no banco (`ArtifactData list obrigacoes` antes). Nunca sobrescreva obrigações, processos ou configurações que o escritório já ajustou.
7. Informe a versão antiga, a nova e o que mudou (veja o CHANGELOG do plugin, se disponível).
