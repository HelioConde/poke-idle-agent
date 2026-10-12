# Validação real do Poke Idle IO

Data: 2026-10-12 (sessão Chrome autenticada, leitura somente).

## Evidência observada

- Rota: `https://pokeidle.io/app`.
- Fonte: árvore de acessibilidade/DOM do Chrome; não foi usado cookie, token,
  armazenamento local, API interna, WebSocket, screenshot OCR ou Canvas.
- O jogo não estava em iframe ou Canvas para esta tela; a árvore DOM acessível
  expôs os controles e valores. Isto não garante o mesmo comportamento em
  abas minimizadas/suspensas.
- Estado observado: treinador `AlchemyFlames` nível 17; Pokémon ativo
  Charmander nível 17, HP `229/276`; time com Charmander e Oddish; farm
  nativo indicado como `caçando`; telemetria de sessão, inventário e as
  automações nativas apareceram no DOM.
- O mapa possui botão semântico `Mapa`, modal `#modal-titulo`, filtro
  `#f-liberadas` e botões de área com `Help` contendo nome e requisito.
  Foram observadas alternativas desbloqueadas de nível 1 (Caterpie, Weedle,
  Pidgey, Rattata, Oddish, Paras, Poliwag, Bellsprout, Geodude e Magikarp)
  e alternativas bloqueadas explicitamente pelo requisito de nível.

## Estado de segurança

- Não houve clique de seleção de hunt, início/parada de farm, evolução,
  inventário, publicação, compra ou venda.
- O farm estava ativo quando o mapa foi aberto. A política exige que ele seja
  comprovadamente parado antes de propor uma troca; portanto a primeira
  seleção real continua bloqueada.
- O executor integrado é um simulador com pós-condições. Ele não possui
  adaptador Chrome real nem é evidência de ação no jogo.
- O Market e a evolução foram identificados como superfícies disponíveis, mas
  não foram abertos nesta sessão, para evitar efeitos não solicitados.

## Catálogo de ação — situação atual

| Ação | Interface identificada | Executor | Validação real |
| --- | --- | --- | --- |
| Observar HUD/time/HP/sessão | DOM acessível | leitura existente | sim, leitura única |
| Listar hunts e bloqueios | modal Mapa, `Help` semântico | planejador | sim, leitura única |
| Selecionar hunt | alvo ainda precisa ser aberto e conferido | simulador | aguardando autorização específica |
| Iniciar/parar farm | estado nativo `caçando` observado | simulador | não executado |
| Inventário | botão `#btn-bolsa` e painel de itens | somente proposta | não executado |
| Evolução | botão `#btn-evoluir` | somente proposta | não executado |
| Market/anúncio/compra | botão Market | somente proposta | não executado |

## Próximo teste real seguro

Após autorização explícita do titular da conta, observar novamente o estado,
parar o farm **somente se a ação também for autorizada**, confirmar o estado
parado, abrir uma hunt alternativa desbloqueada e apresentar o controle final
antes do clique. Só registrar êxito se a observação posterior comprovar a
hunt alvo. Em qualquer divergência, parar sem repetir o comando.

