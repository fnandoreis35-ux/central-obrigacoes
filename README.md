# Central de Obrigações

Programa para Windows que controla as obrigações acessórias do escritório. Ele monta a agenda por competência, mostra prazos e atrasos, envia as guias por e-mail com número de protocolo e registra a ciência quando o cliente responde.

## Instalar

1. Baixe o **CentralObrigacoes-Instalador.exe** na página de [versões](../../releases/latest).
2. Execute o instalador. Não precisa de administrador.
   - Se o Windows mostrar "O Windows protegeu o computador", clique em **Mais informações** e depois em **Executar assim mesmo**.
3. Abra pelo atalho **Central de Obrigações**.
4. Em **Configurações**, preencha o nome do escritório e, mais abaixo, o **e-mail de envio**. Depois clique em **Testar conexão**.
   - **Gmail:** use uma senha de app (Conta Google → Segurança → Verificação em duas etapas → Senhas de app).
   - **Outlook / Microsoft 365:** a Microsoft está desligando o login por senha simples. Pode ser necessário o administrador liberar o "SMTP AUTH" na conta.
   - **Outros provedores** (Locaweb, HostGator, domínio próprio): informe os servidores SMTP e IMAP do provedor.

## Usar

- **Clientes → Importar planilha:** a planilha (Excel ou CSV) precisa ter, na primeira linha, colunas com nome/razão social e CNPJ. Regime, e-mail e responsável são opcionais. As obrigações de cada cliente são marcadas pelo regime.
- **Agenda → Gerar tarefas:** cria as tarefas da competência, com vencimentos ajustados para dias úteis e feriados.
- **Enviar guias:** escolha os PDFs. O programa identifica cliente, obrigação, valor e vencimento. Você confere tudo e confirma o envio. Sai um e-mail por cliente com o protocolo `PRT-AAAAMM-NNNN`.
- **Protocolos → Conferir respostas:** lê a Caixa de Entrada e registra a ciência de quem respondeu. Quem não respondeu pode ser cobrado pelo próprio protocolo.

## Equipe

Cada computador instala o programa normalmente. Para trabalharem na mesma carteira, todos apontam **Configurações → Pasta de dados** para a mesma pasta da rede, por exemplo `\\SERVIDOR\Contabil\CentralObrigacoes`. O e-mail de envio é configurado em cada computador.

Escritórios diferentes usam pastas diferentes, e um não vê os dados do outro.

## Atualizações

Toda vez que é aberto, o programa confere se há versão nova aqui no GitHub. Se houver, baixa só o pacote do programa (poucos KB) e avisa. Os dados não são tocados.

### Publicar uma versão (mantenedor)

1. Altere os arquivos em `programa/app/` e aumente o número em `programa/app/VERSION` (ex.: 1.0.0 → 1.0.1).
2. No GitHub, crie uma **Release** com a tag `v1.0.1` (igual ao VERSION) e escreva o que mudou.
3. O GitHub Actions gera o pacote de atualização e o instalador e anexa os dois à release. Os computadores recebem a atualização na próxima vez que abrirem o programa.

Só é preciso reinstalar quando `LAUNCHER_VERSAO` em `programa/launcher/launcher.py` for aumentado. Isso acontece quando uma biblioteca nova é adicionada, e o programa avisa o usuário.

## Plugin do Claude (opcional)

A pasta `plugins/` traz a mesma rotina como plugin do Claude Cowork, para quem usa o Claude.
