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
