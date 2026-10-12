# Integração PokeGrid-source (MIT) — módulo offline do Idle Game Agent

Referência: https://github.com/soufoka/PokeGrid-source
Versão examinada: main, 49b09094b95ec04302059fe2aadce84a1fcdc726 (2026-10-12).
Autor original: soufoka. Código matemático copiado de
src/domain/iv-math.js para vendor/pokegrid/iv-math.js.
Licença original: MIT, em vendor/pokegrid/LICENSE.

## Por que integração parcial?

O PokeGrid original é um app Electron que oferece painel de até quatro contas,
auto-login, scripts, alteração do loop de renderização, detecção de shiny,
análise de IV, rankings de hunts, relatórios e alertas.

**Licença MIT libera cópia/adaptação do código, mas não substitui
permissão do Poke Idle World.** As regras do jogo proíbem qualquer programa,
script ou extensão não autorizado, automação de ações e macros. Também
restringem multiconte e negociações com botters:
https://poke.idleworld.online/rules

Por isso **não copiamos nem executamos**:
- Electron webviews acessando contas, multi-login, persistência de sessão;
- credenciais, login automático, CAPTCHA, userscript e injeção;
- extensão/navegador/DOM/API/WebSocket do World;
- simulação de cliques, movimentos, trades ou farm;
- controle de quatro contas e rotinas de background;
- telemetria de conta World sem autorização explícita.

A integração usa somente **fórmulas matemáticas puras de IV** com licença
preservada e **relatórios feitos a partir de dados digitados manualmente**.
Os parâmetros de espécies devem vir do próprio usuário; não se deve inventar
níveis, IVs, equipamentos, stats ou hunts.

## Ferramenta 1 — projeção de IV de qualquer Pokémon

Rodar da raiz do projeto:

    node tools/pokegrid_iv_cli.js examples/pokegrid_iv_demo.json

O exemplo é FICTÍCIO. O JSON inclui Pokémon, nível, qualidade, atributos
base fornecidos manualmente, IVs individuais e níveis futuros.

Para usar valores próprios, copie para arquivo ignorado pelo Git:

    copy examples\pokegrid_iv_demo.json data\meus_ivs.json
    notepad data\meus_ivs.json
    node tools/pokegrid_iv_cli.js data/meus_ivs.json

NUNCA cole email, senhas, token, wallet ou identificadores pessoais. Não
enviar esses JSON ao GitHub. Não usa internet; somente o código matemático
do PokeGrid está sendo executado.

A fórmula gera **projeções locais, não confirma ganho de poder no servidor**.
A diferença pode variar por versão do jogo, equipamentos e atualizações.

## Ferramenta 2 — ouro/XP e alertas de farm anotados manualmente

    py -3 -m app.world_pokegrid_report --file examples/pokegrid_snapshots_demo.json

O arquivo contém duas observações com horário ISO 8601 e fuso, contadores
totais de XP, gold, kills, capturas, shiny (contador manual), potions e balls.
As observações precisam pertencer ao MESMO jogo (World), perfil, conta,
Pokémon ativo e hunt para comparação.

    copy examples\pokegrid_snapshots_demo.json data\world_snapshots.json
    notepad data\world_snapshots.json
    py -3 -m app.world_pokegrid_report --file data/world_snapshots.json

Substitua TODOS os valores fictícios por anotações suas. Troque source=demo
por source=manual para identificar as medições anotadas de fato.

O relatório mostra XP/h, variação LÍQUIDA de gold/h, kills/h, capturas/h,
consumo de potions/balls e projeção de horas restantes quando houver consumo
observado. Também avisa se não houve kill na janela medida ou se você marcou
nova captura shiny. Não acessa dados da conta.

**Gold/h líquido não é lucro financeiro.** Ganhos em USDT são sempre null,
sem saque oficial e comprovado. Custos, gold gasto e compras podem afetar o
resultado líquido; não deduzir rendimento monetário.

## Painel integrado

O painel local pode exibir o relatório manual, sem ativar integração com
o World:

    py -3 dashboard.py --world-report data/world_snapshots.json

Depois abra http://127.0.0.1:8767 no navegador.

Se você não informar --world-report, a área permanece desativada. O servidor
escuta somente 127.0.0.1 e o endpoint /api/world-pokegrid aceita apenas GET.

O painel não lê outros arquivos sem o parâmetro; não recebe upload nem envia
informações ao jogo. Os dados demonstrativos sempre são rotulados como tal.

## Como validar

    py -3 -m unittest discover -s tests -v
    node tests/test_pokegrid_iv.js
    node --check vendor/pokegrid/iv-math.js
    node --check tools/pokegrid_iv_cli.js

CI testa Python, JavaScript e launchers Windows. Não exige Electron, login,
captura do jogo, API de terceiros ou operação de contas.

## Próximas funcionalidades possíveis

- Comparação de hunts com histórico CSV manual mais rico, sem inferir chances.
- Projeto de time com cenários de IV e composição.
- Alertas de recursos usando dados MANUAIS, sem capturar a sessão World.
- Novos modos só se a equipe do Poke Idle World der autorização clara e
  específica; registrar essa autorização antes de introduzir integração.

Para funções multi-conta, scripts e login automático, consulte o PokeGrid
separadamente e avalie as regras do jogo antes de utilizar qualquer programa
externo. Não instalar nem executar esse software automaticamente pelo IGA.

O objetivo comprovado de Gems/USDT permanece exclusivo do Poke Idle IO,
sem reinterpretação de gold ou diamantes do World.
