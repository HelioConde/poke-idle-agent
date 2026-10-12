# Checklist de continuidade

## Concluído e testado localmente

- Descoberta de abas por extensão, incluindo abas inativas, com isolamento por perfil.
- Separação de Poke Idle IO e World; World não aceita telemetria de conta.
- Diagnóstico de rota, DOM, Canvas e iframe sem copiar HTML, credenciais ou dados de login.
- Normalização conservadora de HUD IO e XP/h apenas entre amostras válidas.
- Memória SQLite local de observações normalizadas e decisões dry-run, separada por perfil/sessão.
- Livro-caixa SQLite por jogo, perfil e conta; distingue ativo obtido, anúncio,
  venda concluída, saque solicitado e USDT manualmente confirmado.
- Métricas de farm por deltas observados; valores ausentes não são estimados.
- Decisões explicáveis em dry-run e executor com pausa, limite e parada de emergência.
- Simulador local de observe → plan → act → verify.
- Testes Python, JavaScript e verificações de launchers Windows.
- Integração em worktree dos módulos `io_action_engine` e
  `io_operation_planner`, sem substituir os módulos locais de economia,
  livro-caixa, controle, política e memória.
- Validação real somente-leitura do DOM autenticado em `/app`; o relatório
  com fonte, limites e estado das ações está em `IO_REAL_VALIDATION.md`.

## Bloqueado por validação externa

- Validar a leitura da extensão em segundo plano/minimizada. A leitura manual
  autenticada confirmou DOM sem Canvas/iframe na aba ativa, mas não prova o
  comportamento de renderização em abas suspensas.
- Implementar e validar um adaptador Chrome real por ação. O código integrado
  possui somente `FakeIOAdapter`; `verified_actions` não é prova suficiente
  para habilitar o modo live.
- A primeira troca de hunt está aguardando autorização humana específica. O
  farm estava ativo na observação e deve ser parado/comprovado antes de trocar.
- Os termos públicos do IO, atualizados em 30/09/2026, permitem automação no jogo e
  no Market. Ainda falta validar em conta cada controle, pré-condição e resultado antes
  de habilitar ação real. A lista de execução real continua vazia.
- Qualquer integração de conta, captura visual ou automação no Poke Idle World requer
  autorização explícita da equipe; ela não está implementada.
- Mercado, inventário, equipe, evolução e breeding dependem de interfaces confirmadas e
  continuam somente como dados não observados, sem ações de venda, compra ou consumo.
- GitHub Actions precisa ser disparado no remoto; os comandos equivalentes locais passaram.

## Próximo procedimento de desbloqueio

1. Iniciar `INICIAR-MONITOR-ABAS.bat`, carregar a extensão e parear a chave local.
2. Abrir manualmente `/app`, recarregar a extensão e a página, e coletar o diagnóstico do
   painel sem publicar token, screenshot privado ou HTML.
3. Se os indicadores forem DOM, adicionar somente seletores comprovados e testes de parser.
   Se forem Canvas, registrar a limitação e validar captura permitida antes de OCR.
4. Reexecutar a suíte completa e documentar o resultado real como real, não simulado.

## Informação pública conferida em 2026-10-11

- A rota `/app` expõe tela de login e, sem autenticação, um HUD público de nível no
  formato `— Nv 1`; o adaptador reconhece esse formato e continua ignorando `input`.
- A própria interface lista automações nativas para captura, revive, poções e retorno
  à hunt. O projeto não envia comandos externos para esses controles; o usuário pode
  usar as automações oficiais manualmente enquanto a extensão permanece somente leitura.
