# Auditoria de controles — Poke Idle IO

Data da evidência inicial: 2026-10-12. A inspeção foi somente leitura na rota
`https://pokeidle.io/app`; nenhum controle foi acionado.

| Capacidade | Evidência DOM | Estado | Consequência |
| --- | --- | --- | --- |
| Painel do treinador | `.tr-dados` | leitura auditada | Nível e XP do treinador só são aceitos nesse contexto. |
| Pokémon ativo | `.ativo-info` | leitura auditada | Mantido separado da XP do treinador. |
| Inventário | `#btn-bolsa` | leitura de presença | Abrir/listar conteúdo ainda requer revisão de menu e não é executável. |
| Estado de sessão | `#eco-painel` com marcador `caçando` | leitura indicativa | Informa `active` apenas quando o texto está presente; ausência permanece `unknown`. |
| Desistir | `#eco-desistir` | bloqueado permanentemente | Pode causar derrota/perda de XP. Nunca é pausa, parada ou alvo de execução. |
| Botão Mapa | `button[data-modal="mapa"]` | candidato de leitura | Seletor encontrado em referência externa; confirmar na sessão real. Não aciona menu. |
| Janela Mapa | `#modal .modal-caixa[data-modal="mapa"]` | candidato de leitura | `map_state` indica aberto/fechado/desconhecido; não seleciona hunt. |
| Captura nativa | `#auto-ball-captura`, `#auto-ball-sem-parar` | somente leitura | Presença e estado observado do checkbox, sem alteração. |
| Recuperação nativa | `#auto-revive`, `#auto-potion`, `#auto-voltar-hunt` | somente leitura | Presença e estado não comprovam segurança para acionamento. |
| Iniciar farm | nenhum controle distinto confirmado | não auditado | Não há execução. |

## Protocolo de promoção de uma ação

Uma ação só pode ser candidata a execução depois de existir, no mesmo commit,
um seletor estável, rota, pré-condições, pós-condição mensurável, análise de
risco, teste de adaptador e autorização humana específica para o primeiro
clique. A evidência deve então ser adicionada a
`app/io_local_live_controls.py`; telemetria, IA e o próprio adaptador não
podem alterar essa lista.

Compras, vendas, anúncios, evolução, depósitos, saques e qualquer operação do
Poke Idle World permanecem fora do executor.

## Referências técnicas externas (consultadas, sem código copiado)

- [Launcher Alt: PokeIdle](https://github.com/henriquecodo/launcher-alt-pokeidle):
  documenta controles nativos (`auto-*`) e navegação do Poke Idle IO.
- [Hunt Atlas](https://github.com/MOTHblank/pokeidle-huntatlas):
  referência de leitura do modal Mapa (`#modal`, `.modal-caixa`, `#modal-corpo`).
  Não foi importado o código do script nem o envio de mensagens internas.
- [Rebosteio Launcher](https://github.com/souonailo/rebosteio-launcher-pokeidleio):
  fixture do menu `button[data-modal="mapa"]` em uma versão documentada por terceiros.

O leitor foi implementado de forma original, baseado em seletores pesquisados.
Esses seletores são **candidatos** até confirmação na versão real atual do jogo.
Nenhuma biblioteca externa foi incorporada como dependência e nenhum clique,
WebSocket, login ou comando de gameplay foi importado.

### Formato novo da auditoria

O payload acrescenta `map_state: "open" | "closed" | "unknown"`.
Os controles nativos podem incluir `toggle_state: "on" | "off" | "unknown"`;
isso representa apenas a leitura do checkbox, nunca um comando ou autorização.

O servidor valida nomes, políticas, estados e seletores com uma lista fechada.
Payloads arbitrários são rejeitados; o formato anterior, sem `map_state`,
continua aceito para compatibilidade com leitores antigos.

**Próximo teste real:** verificar as referências na versão atual de
`https://pokeidle.io/app` e analisar se selecionar uma hunt afeta farm ativo.
Até revisão e aprovação humana específicas, `select_hunt`, `start_farm`,
`stop_farm` e modo live permanecem bloqueados; o registro local segue vazio.


## Evolução do monitor por referências dos launchers

Inspirado na apresentação de XP/h por conta do Launcher Alt, o painel agora
mostra médias do treinador por **aba e janela Chrome**, com três períodos:
5, 15 e 60 minutos. Cada período só aparece quando há pelo menos 80% de sua
duração coberta por amostras numéricas válidas da mesma barra e do mesmo nível.
Intervalos sem dados confiáveis, leituras incompatíveis, queda de XP ou mudança
de nível encerram a série e removem taxas que não podem ser verificadas.

As séries ficam apenas em memória e são limitadas a 60 minutos e 1.024
amostras por aba. Sem autenticação da identidade do treinador no payload,
**o perfil/aba não é prova de conta**. Portanto as médias não são ainda uma
medida certificada por conta/hunt e não podem autorizar mudanças automáticas.
O painel distingue explicitamente médias maduras de janelas pendentes.

A auditoria também é exibida separadamente para todas as abas IO registradas,
em vez de exibir apenas a primeira. O estado dos controles continua sendo
somente leitura e não concede poder ao executor live.

## Diagnóstico do encontro e estrutura do Mapa (extensão 0.2.5)

Uma fixture pública do Poke Idle IO expõe `#hud-hunt` e `#eco-onde`
com texto como `Larvitar · nível 30`. Isso pode ser **o Pokémon do encontro**,
e não o nome da hunt. O monitor corrige a interpretação anterior e apresenta
essa leitura como **contexto visual do encontro**, sem associá-la a localização.
Não acessa WebSocket, cookies, estado privado ou APIs internas do jogo.

- Se dois indicadores contiverem o mesmo nome e nível, a pista terá
  `status: matching_displays` (concordância visual, não verificação).
- Com um só indicador íntegro, `status: single_display`.
- Se houver duas leituras diferentes, `status: ambiguous`, sem nome ou nível.
- Sem leitura íntegra, `status: unavailable`.

O objeto fechado `hunt_hint` contém apenas
`{status, label, level, source}`. Nomes são limitados a 48 caracteres,
caracteres restritos e nível de 1 a 10000. Não aceita HTML, URLs,
e-mails, textos de chat, tokens, seletores nem campos extras.
A leitura está disponível somente na rota `/app`.

**Importante:** o rótulo visível do encontro **não identifica hunt_id, área
ou slug**, mesmo quando os dois indicadores coincidem. Não comprova a conta
ou a hunt no servidor; o novo dado não alimenta o ranking do comparador,
não promove controles para execução e não autoriza navegação.
O primeiro teste com o DOM real do Chrome continua pendente.

Referência: fixture `test/fixtures/center-hunt.html` do
[Rebosteio Launcher](https://github.com/souonailo/rebosteio-launcher-pokeidleio).
Seletores tratados como candidatos até validação real; nenhuma rotina externa
copiada ou importada.

### Auditoria estrutural do menu Mapa

Quando o modal `#modal .modal-caixa[data-modal="mapa"]` estiver aberto,
a extensão inspeciona apenas `#modal-corpo` e informa **contagens**:
`buttons`, `links` e `candidate_markers` (elementos com atributos
`data-hunt`, `data-hunt-id` ou `data-slug`). Cada valor é limitado a 200.
Nenhum texto, HTML, URL, slug ou nome é enviado ao servidor.

O campo fechado `map_structure` recebe `status: observed`,
`body_missing` ou `not_open`. Sem o mapa aberto, as contagens ficam zero.
O servidor rejeita campos extras, valores inválidos ou estados incompatíveis
com `map_state`. Essas contagens servem apenas para diagnosticar como é
construída a UI real; **não provam quantidade de hunts, acesso ou autorização**.

A leitura do DOM real após recarregar a extensão segue pendente. Até esse
teste, os seletores são referências externas não confirmadas no Chrome do
usuário. A política do executor continua bloqueando `Desistir`, troca de
hunt, início de farm e qualquer operação financeira.


### Conferência com captura estática do DOM (13/10/2026)

O usuário forneceu uma captura HTML da interface autenticada do IO.
A análise foi **local**: nenhum HTML bruto, dado da conta, imagem base64,
nick, saldo, URL de sessão, item privado ou token foi incorporado ao GitHub.

Foram confirmados nesta captura: o botão `button[data-modal="mapa"]`,
`#modal.hidden`, a caixa `#modal .modal-caixa[data-modal="mapa"]`,
`#modal-corpo`, as áreas `.mapa-areas .mapa-area[data-regiao]` e os
marcadores `#mapa-tela button.marcador[data-slug][data-travado]`.

Na captura com modal FECHADO, existem 8 botões de regiões renderizados
(2 sem a classe de trava) e 14 marcadores renderizados (8 com
`data-travado="0"`, 1 com a classe `on`). Esses totais descrevem
o **DOM pré-renderizado e filtrado**, não uma lista definitiva de hunts
acessíveis nem a hunt que está sendo farmada.

### Leitura refinada na extensão 0.2.6

`map_structure` passa a disponibilizar, somente enquanto o Mapa está
visivelmente aberto:

- `rendered_regions` e `available_regions` — botões renderizados,
  com ou sem a classe de bloqueio
- `rendered_markers` e `unlocked_markers` — marcadores visíveis no
  catálogo atual, separados por `data-travado`
- `highlighted_markers` — quantidade de marcadores com classe `on`,
  **sem presumir que significa hunt ativa**

Todos os campos são contagens de 0 a 200. Não são transmitidos nomes,
slugs, regiões, marcadores individuais, HTML ou coordenadas.
O servidor permite o formato anterior da extensão 0.2.5 para
compatibilidade, mas exige que os cinco campos novos sejam enviados juntos,
com quantidades consistentes. Com o Mapa fechado, todas as contagens
permanecem zeradas, mesmo que o jogo tenha montado os nós ocultos.

A próxima validação é **no Chrome, com extensão recarregada e Mapa aberto
manualmente**. Nenhum clique de navegação ou gameplay foi habilitado.

### Evidência visual da cena — versão 0.2.7

A captura HTML enviada da interface IO mostra a classe `hunt-ativa` no
elemento `#palco`, enquanto `#centro-curar` está oculto. Isso permite
registrar que o **palco exibido** parece ser o de uma hunt, mas **não comprova
que o servidor do jogo está farmando ou batalhando**. O leitor original
passa a produzir uma enumeração estritamente fechada:

- `hunt_scene`: `#palco.hunt-ativa` e nenhuma indicação visual de Centro
- `center_scene`: `#palco.centro-ativo` e `#centro-curar` exibido
- `conflict`: sinais de cena de hunt e Centro simultâneos
- `unknown`: ausência ou inconsistência das evidências visuais

O novo campo `scene_indicator` só é aceito pelo validador na rota `/app`;
para outras rotas, somente `unknown`. A estrutura anterior da extensão
continua suportada. O monitor deixa claro quando o texto de `#eco-painel`
apenas **sugere atividade**.

Esta medição não muda `farm_state`, `advice`, permissões, execução do
adaptador ou ranking de hunts. Não transmite texto do palco, botões, nome,
conta, equipe, HTML nem dados do combate. `Desistir` continua proibido.
Os cenários de hunt, Centro, conflito e rota diferente estão cobertos por
testes offline. A confirmação da cena no **Chrome real**, após recarregar a
extensão e a página, ainda é necessária.
