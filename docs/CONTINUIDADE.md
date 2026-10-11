# Checklist de continuidade

## Concluído e testado localmente

- Descoberta de abas por extensão, incluindo abas inativas, com isolamento por perfil.
- Separação de Poke Idle IO e World; World não aceita telemetria de conta.
- Diagnóstico de rota, DOM, Canvas e iframe sem copiar HTML, credenciais ou dados de login.
- Normalização conservadora de HUD IO e XP/h apenas entre amostras válidas.
- Memória SQLite local de observações normalizadas e decisões dry-run, separada por perfil/sessão.
- Métricas de farm por deltas observados; valores ausentes não são estimados.
- Decisões explicáveis em dry-run e executor com pausa, limite e parada de emergência.
- Simulador local de observe → plan → act → verify.
- Testes Python, JavaScript e verificações de launchers Windows.

## Bloqueado por validação externa

- Confirmar os seletores do HUD autenticado de `https://pokeidle.io/app` e verificar a
  leitura em segundo plano. Sem essa evidência, o adaptador continua reportando DOM/Canvas
  vazio em vez de fabricar métricas.
- Confirmar, para cada controle do IO, termos vigentes e uma ação de baixo risco autorizada
  antes de incluir qualquer item na lista de ações reais. A lista atual para IO é vazia.
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
