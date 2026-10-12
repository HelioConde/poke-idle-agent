# World: plano de progresso do Charizard nível 110

**Uso OFFLINE, manual e independente do navegador.** Nenhum bot, extensão de
leitura de conta, acesso a WebSocket, login ou comando do World é implementado.

## Prioridades diferentes entre jogos
- **Poke Idle World:** medir XP/h e GOLD LÍQUIDO/h, melhorar a evolução e
  chegar a hunts que o time consegue vencer. Não confundir gold/diamante com R$.
- **Poke Idle IO:** preservar o motor econômico de Gems e USDT e as metas
  de 1.000 Gems + primeiro saque realmente confirmado, conforme
  docs/OBJETIVO_PRINCIPAL.md.
- Não aplicar as taxas, ranking por USDT ou meta de saque do IO ao World.

## Plano prático nível 110

1. **Espécie confirmada: Charizard nível 110.** Já evoluído. Precisamos
   do nível do TREINADOR para saber quais hunts são acessíveis. Treinador
   e Pokémon possuem níveis diferentes.
2. **Não há evolução pendente para esse Charizard.** O alerta de
   evolução gratuita reiniciar o nível não é uma ação recomendada para
   o Pokémon que você já evoluiu.
   Como Fogo/Voador, avalie fraquezas a Pedra (especialmente), Água e
   Elétrico conforme os cálculos de tipos do World.
3. Ative as rotinas **nativas** Auto-Potion e Auto-Revive se fizerem sentido;
   Auto-Catch depende de VIP. **Não usar macros, cliques simulados ou
   programas externos não autorizados.**
4. Use o Zzz nativo quando quiser sair do navegador: precisa ativar a
   função, que inicia amostra de 5 minutos. Fechar simplesmente a aba
   não equivale a iniciar esse modo.
5. O guia comunitário cita hunts Houndoom e Charizard para nível 100–150
   em rotas preparadas, mas não são necessariamente boas para um Charizard
   do tipo Fogo/Voador. Teste tempo de abate, dano recebido, XP e gold líquido em
   pelo menos duas hunts adequadas à sua equipe e nível de treinador.
6. Preserve itens raros e acompanhe o mercado apenas pelas funções oficiais.

## Como medir manualmente

No PowerShell, na raiz do repositório:

    py -3 -m app.world_manual_planner --species Charizard --pokemon-level 110

Faça uma cópia de examples/world_hunts_demo.csv em data/world_hunts_manuais.csv
e SUBSTITUA tudo por dados medidos por você dentro do jogo:

    hunt,minutes,xp_gained,gold_gained,expenses_gold,source
    Hunt real 1,30,12000,5000,100,manual
    Hunt real 2,30,11000,6300,250,manual

Os números acima são apenas ilustração, não resultados do jogo.

    py -3 -m app.world_manual_planner --species Charizard --pokemon-level 110 --trainer-level 95 --csv data/world_hunts_manuais.csv --priority gold

O nível 95 acima também é exemplo; informe seu nível verdadeiro.

A classificação exige duas hunts com 30 minutos cada e somente dados de
origem manual. Não chama o site nem pode automatizar nada.

## Monetização

O site oficial World documenta mercado em gold/diamantes, porém não
localizamos fluxo de saque oficial equivalente ao de USDT/Gems do IO.
Ofertas em sites de terceiros não comprovam transação, liquidez, segurança,
permissão das regras nem recebimento. As regras World proíbem ferramentas e
extensões sem permissão da equipe, macros e comércio com botters.

## Fontes

- https://poke.idleworld.online/rules
- https://poke.idleworld.online/pokepedia/systems/evolution
- https://poke.idleworld.online/pokepedia/systems/vip
- https://poke.idleworld.online/pokepedia/systems/offline
- https://poke.idleworld.online/pokepedia/systems/xp
- https://www.don-devs.com.br/guia-iniciante

## Proteção dos commits locais da economia

Os SHAs 7ff3fcf e cc4f0f8 informados pelo usuário não aparecem no GitHub
origin/main nem nas branches remotas consultadas. NÃO fazer merge, reset,
rebase ou cherry-pick automático. Esses commits podem existir apenas no PC.
Manter esta branch de planejamento isolada de toda implementação econômica
até revisar o log local e fazer backup.
