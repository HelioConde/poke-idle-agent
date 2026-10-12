# Arquitetura adaptativa — novas contas e qualquer Pokémon

O **Idle Game Agent não é um bot de Charizard**. Ele é um planejador
generalista, com estado por jogo, perfil, conta, equipe e Pokémon ativo.
Charmander, Charizard e quaisquer outras espécies são exemplos, nunca
constantes de configuração. Não há pressuposto sobre seu nível.

## Modelo por conta

Uma sessão é identificada pela combinação:
`(game, profile_id, account_id)`.

Os identificadores são apelidos locais, **nunca e-mail/senha/ID real de conta**.
Cada conta informa de maneira independente:

- jogo (IO ou World);
- nível do treinador (opcional até ser conhecido);
- lista de Pokémon de qualquer espécie e nível, com HP opcional;
- qual Pokémon está atualmente ativo;
- hunts disponíveis, bloqueadas ou ainda desconhecidas;
- amostras de resultados verificadas, separadas por hunt **e Pokémon ativo**.

Sem alguma dessas informações, o programa pergunta pelo dado ausente por
meio de uma recomendação de descoberta, em vez de inventar níveis ou hunts.

### Estágios automáticos

| Situação | Estágio | Saída |
|---|---|---|
| Equipe vazia | `onboarding` | Registrar starter |
| Equipe sem Pokémon ativo | `team_setup` | Selecionar ativo |
| HP baixo medido | `survival` | Avaliar recuperação |
| Nível de treinador desconhecido | `discovery` | Registrar nível |
| Hunts ainda bloqueadas | `unlock` | Verificar acessos reais |
| Menos de duas hunts medidas | `measurement` | Medir mais |
| Hunts comparáveis válidas | `optimization` | Comparar XP/recursos/derrotas |
| Objetivo monetário sem histórico de vendas IO | `market_research` | Medir vendas e liquidez |
| Objetivo monetário com vendas comparáveis IO | `market_optimization` | Revisar oportunidade em dry-run |
| Objetivo USDT no World | `unsupported` | Sem saque oficial verificado |

A máquina de estados usa **capacidade, informação e risco**, não limites de
nível arbitrários. Requisitos de desbloqueio são inseridos dos dados
observados/manuais e nunca são inventados pela IA.

### Comparação com evidências

A comparação de hunts requer:
1. Duas hunts explicitamente desbloqueadas.
2. Pelo menos 30 minutos por hunt (amostras podem ser agregadas).
3. Mesma conta/perfil/jogo.
4. Mesmo Pokémon ativo — métricas do Pokémon reserva não são misturadas.
5. Origem `manual` no World; `manual` ou `observed` no IO.
6. Exemplos `demo` nunca contam como evidência.

Calcule XP/h, **recursos líquidos por hora** e derrotas/h. A estratégia
`xp` prefere XP, `resources` prefere recursos, `balanced` combina as
duas dimensões e todas penalizam derrotas. Não converter recursos em USDT.

No **IO**, o objetivo `monetization` usa o motor econômico local: uma
evidência só participa quando pertence à mesma `(game, profile_id, account_id)`,
tem origem `manual` ou `observed` e ao menos três vendas concluídas comparáveis.
O ranking considera Gems líquidas esperadas, probabilidade de venda e
confiança; não usa XP como substituto de liquidez. O projeto *não afirma*
saque/comercialização finalizada.

No **World**, só há análise **manual e offline**. Não usa APIs, content
scripts de coleta de conta, WebSocket, bot, macro, clique ou login.
Respeitar https://poke.idleworld.online/rules .

### Exemplos executáveis

Execute em uma cópia/worktree limpa (preserve qualquer branch local
que contenha os commits econômicos não publicados):

    python -m unittest discover -s tests -v
    python -m app.adaptive_strategy --accounts examples/adaptive_accounts_demo.json --measurements examples/adaptive_measurements_demo.json
    python -m app.adaptive_strategy --accounts examples/adaptive_accounts_demo.json --objective monetization

Os exemplos são **inteiramente sintéticos** e retornam
`measurement`/`market_research`; não demonstram rendimento nem acesso
a contas reais.

Para sua coleta manual, copie esses JSON para `data/`
(pasta ignorada pelo Git), substitua com seus próprios dados e use
`--accounts data/minhas_contas.json --measurements data/minhas_medicoes.json`.
Para a análise de mercado, use também
`--objective monetization --market data/minhas_vendas_concluidas.json`; cada
registro deve conter `game`, `profile_id`, `account_id`, `name`,
`expected_net_gems_per_hour`, `sale_probability`, `confidence`,
`comparable_completed_sales` e `source`. Os valores são estimativas derivadas
de vendas concluídas, não anúncios nem USDT.

Não inclua senhas, tokens, dados pessoais, cookies, carteiras ou números
de conta. Envie ao ChatGPT apenas dados anônimos ou métricas agregadas.

### Proteção do trabalho do Copilot

Em 11/10/2026 o repositório remoto apresentou somente as branches
`main` e `feat/world-level110-manual-planner`. Os commits locais de
motor econômico citados pelo usuário (`7ff3fcf` e `cc4f0f8`)
não estavam publicados. Esta arquitetura foi criada em
`feat/adaptive-multi-account-agent` sem tocar na `main`.
Antes de mesclar, faça backup dos commits econômicos locais e execute
um merge/rebase revisado, preservando os testes e o contrato financeiro.
