teste
linha 2# Central de Obrigações: plugin para Claude Cowork

Controle de obrigações acessórias com agenda por competência, radar de prazos, envio de guias por Gmail com protocolo e registro da ciência do cliente.

## Para quem vai usar

1. No Claude (app desktop), abra **Personalizar → Plugins → Adicionar marketplace** e informe este repositório do GitHub.
2. Instale o plugin **central-obrigacoes**.
3. Conecte o **Gmail** em Conectores.
4. Numa conversa, peça:
   - **Escritório novo:** "instalar a central de obrigações". O Claude cria um painel vazio só seu, com o catálogo de obrigações.
   - **Equipe de um escritório que já usa:** peça ao dono o link do painel (compartilhado com permissão de edição) e cole na conversa.
5. Depois é só pedir, por exemplo: "importar minha carteira", "gerar a agenda de 10/2026", "o que vence esta semana", "enviar as guias de 09/2026".

Os dados (clientes, tarefas, protocolos) ficam no painel de cada escritório. Nenhum escritório vê os dados de outro.

## Atualizações

Quando sair uma versão nova, o app mostra a atualização do plugin. Se a versão nova mudar o painel, peça ao Claude "atualizar o painel": ele troca só a tela e mantém todos os dados.

## Para o mantenedor (publicar uma versão)

1. Edite os arquivos em `plugins/central-obrigacoes/`.
2. Se mudou o painel (`skills/painel-obrigacoes/assets/painel.html`), aumente a versão nas **duas** marcações dentro dele (`<meta name="central-obrigacoes-versao">` e `PAINEL_VERSAO`).
3. Aumente `version` em `plugins/central-obrigacoes/.claude-plugin/plugin.json` **e** em `.claude-plugin/marketplace.json` (ex.: 1.0.0 → 1.1.0).
4. Anote a mudança no `CHANGELOG.md` e envie (commit/push) para o GitHub.

Sem aumentar a versão, quem já instalou não recebe a atualização.
