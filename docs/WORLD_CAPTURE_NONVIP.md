# Captura para contas sem VIP — planejamento original, sem bot externo

Origem da ideia: https://github.com/PollitoScripts/Poke-Idle-World-Auto-Catch

## Avaliação do projeto de terceiros

O repositório PollitoScripts contém um único README com userscript Tampermonkey que dispara automaticamente Throw e utiliza outros mecanismos de observação da página. Não foi encontrado arquivo LICENSE ou autorização clara para copiar/redistribuir o código. Nosso módulo foi desenvolvido de maneira independente.

## Regras oficiais

- https://poke.idleworld.online/rules — o Poke Idle World proíbe programas, scripts e extensões sem autorização da equipe; também veda autoclickers e macros que realizem repetidamente ações. Mais de quatro contas sem permissão ou justificativa aceita podem resultar em sanções.
- https://poke.idleworld.online/pokepedia/systems/vip — Auto-Catch é um recurso VIP, Auto-Potion é gratuito. A ferramenta externa não substitui esses termos.

## O que foi implementado

O módulo app/world_capture_assistant.py oferece até quatro contas distintas por apelido, sem credenciais, com:
- políticas de Pokébolas próprias de cada conta;
- prioridades diferentes para encontro normal e shiny;
- reserva de Pokébolas raras para shinies;
- histórico de tentativas/capturas digitado manualmente;
- sugestão manual da próxima Pokébola, somente quando o encontro foi confirmado pelo titular;
- modo VIP que recomenda usar o Auto-Catch oficial dentro do jogo;
- alertas para falta de Pokébolas e origem demonstrativa separada de anotações reais.

O módulo NUNCA clica em Throw, executa scripts na página, intercepta WebSocket, abre sessões, fornece captcha, roda macros ou automatiza contas World. Não há funcionalidade de bot a ativar nesta branch.

## Como testar

Na raiz do repositório, execute:

    py -3 -m app.world_capture_assistant --file examples/world_capture_demo.json

Para configurar suas contas anônimas reais, copie o exemplo para data/world_capture.json (a pasta data é ignorada pelo Git), atualize os números e informe source: manual, sem transformar observações fictícias em reais.

No Windows:

    if not exist data mkdir data
    copy examples\world_capture_demo.json data\world_capture.json
    notepad data\world_capture.json
    py -3 -m app.world_capture_assistant --file data\world_capture.json

Cada conta contém profile_id, account_id, vip, inventory, shiny_reserves, normal_priority, shiny_priority, encounter e attempts. Marque encounter.confirmed somente após ver o encontro manualmente. Se o encontro não estiver confirmado, não há sugestão de lançamento.

Exemplo de prioridades:

    normal_priority: ["Poke Ball", "Great Ball", "Ultra Ball"]
    shiny_priority: ["Idle Ball", "Ultra Ball", "Great Ball"]
    shiny_reserves: {"Idle Ball": 1, "Ultra Ball": 2}

As reservas são protegidas nos encontros normais e ficam disponíveis quando o encontro é shiny. Os resultados não estimam chance de captura nem rendimento financeiro sem evidência.

## Painel local

    py -3 dashboard.py --world-capture data/world_capture.json

Abra http://127.0.0.1:8767 para consultar planos por conta. O endpoint /api/world-capture é somente GET; não aceita comandos de gameplay.

Também é possível combinar com a análise PokeGrid:

    py -3 dashboard.py --world-capture data/world_capture.json --world-report data/world_snapshots.json

## Testes

    py -3 -m unittest discover -s tests -v

Inclui regressões de isolamento de contas, proteção de reservas, não-VIP/VIP, histórico manual, campos sensíveis rejeitados, fonte demo e impossibilidade de executar captura externa.

## Integração real no futuro

Se a equipe do World autorizar explicitamente uma integração externa para não-VIP, reavaliar as regras e o escopo, registrar autorização verificável e só então projetar adaptador com limites, testes e confirmação. A disponibilidade de código público ou de uma licença aberta não é autorização para automação dentro do jogo.

**Nenhuma automação externa do World foi ativada.**
