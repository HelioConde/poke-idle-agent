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
| Mapa/hunt | botão visual sem ID estável observado | não auditado | Não há selector cadastrado, nem execução de seleção de hunt. |
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
