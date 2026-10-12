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

## Tentativa real de seleção — interrompida com segurança

Em 2026-10-12 o titular autorizou o teste inicial. A observação prévia
confirmou farm ativo. O único controle oficial localizado para interrompê-lo,
`Desistir`, exibiu antes da confirmação que ele derrotaria a equipe, levaria
o Pokémon ao Centro e descontaria **517 XP** (10% do nível do treinador).
Essa consequência não correspondia a uma simples parada de farm. O diálogo
foi cancelado e a telemetria posterior continuou mostrando `caçando`.

Resultado: **nenhuma hunt foi alterada, nenhum XP foi perdido e o teste não
foi marcado como sucesso**. O mapa permaneceu aberto, e o DOM também expôs
o analisador da hunt atualmente inspecionada (Graveler), com estimativas e
drops; isso não foi tratado como confirmação de uma troca.

## Teste operacional autorizado — estado inconsistente após parada

Em uma autorização posterior, o controle `Desistir` foi confirmado uma única
vez depois de expor o custo de **549 XP**. A interface então apresentou
`Centro Pokémon · Cerulean`, o botão `Curar equipe` e a mensagem `Seu time
está no chão!`, sinais de que o combate foi interrompido. Porém, o painel de
sessão simultaneamente ainda informava `caçando`. Pela política de falha
fechada, este conflito torna o estado do farm desconhecido. Não foi executada
nenhuma seleção de hunt, reinício do farm ou segunda tentativa.

Resultado desse teste: **falhou o critério composto** (não há comprovação
consistente de farm parado; hunt não foi alterada). A correção necessária é
modelar separadamente o estado transitório do Centro/derrota e esperar uma
observação estável antes de liberar seleção.

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


## Remediação do incidente — trava de segurança (branch separada)

**O controle `Desistir` é uma rendição com derrota e penalidade, NÃO uma pausa
ou um `stop_farm` seguro.** Não usar esse botão novamente como parte da
rotina de troca de hunt. Não há método alternativo de pausa sem custo
identificado e validado nesta sessão.

O modal exibiu penalidade de **549 XP**. A leitura registrada de XP do
treinador caiu de **5.490 para 4.949**, ou **541 XP líquidos observados**.
Essas quantias não são iguais: pode ter havido outra atualização de XP no
intervalo, mas a causa da diferença não foi comprovada. Não afirmar
perda líquida de 549 como se fosse o delta medido.

Mudanças defensivas publicadas separadamente em
`fix/io-desistir-xp-loss-guard`:
- Recusar `stop_farm` em modo live no executor, independentemente de o
  adaptador declarar essa ação como validada; a lista de controle seguro
  segue vazia.
- O planejador **não gera `stop_farm`** para troca de hunt ou HP baixo
  enquanto não existir método de parada seguro.
- Distinguir sinais de **Centro Pokémon**, **equipe derrotada**, indicador
  de farm, status do painel de sessão e **XP do treinador**.
- Bloquear qualquer comando em caso de Centro, derrota, status conflitante
  ou perda de XP pós-ação.
- Exigir duas leituras reais da mesma conta, rota/hunt e estado, datadas
  **2 a 60 segundos** entre si, antes de sequer considerar uma seleção
  de hunt ou início de farm. Falta de timestamp/sinal = estado desconhecido.
- Testes de regressão em `tests/test_io_desistir_safety.py`.

**Importante:** as proteções novas ficam no planejador e executor Python.
Elas não se instalam automaticamente em uma ferramenta de navegador externo
ou numa sessão Codex já iniciada. Configure qualquer agente/browser com o
mesmo veto explícito antes de permitir outra interação.

### Procedimento permitido agora: SOMENTE LEITURA

1. Não clicar em Desistir novamente nem selecionar hunt enquanto a equipe
   estiver no Centro Pokémon ou o painel indicar `caçando` de forma
   contraditória.
2. Inspecionar, sem cliques de jogo, duas observações do HUD e do painel
   de sessão. Conservar origem, timestamp, tela atual, HP, situação da
   equipe, farm, hunt e XP do treinador em log sanitizado.
3. Não curar automaticamente; qualquer recuperação deve ser iniciada
   manualmente e conscientemente pelo titular.
4. Buscar em documentação/interface um controle genuinamente reversível e
   sem custo de pausa de hunt. Não inferir que `Desistir` serve.
5. Somente planejar um **novo** teste com autorização específica após a
   interface estar coerente, o estado estar estável e as consequências do
   botão serem conhecidas. Nenhuma autorização anterior se transfere.

**O teste ocorrido continua reprovado e NÃO é autorização para repetição.**
