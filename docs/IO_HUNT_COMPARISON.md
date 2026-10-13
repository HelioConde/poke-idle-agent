# Comparador de hunts — Poke Idle IO

Este módulo é **somente consultivo**. Nenhuma recomendação executa ações,
envia comandos ao jogo ou habilita controles no adaptador live.

## Como preencher

O painel procura dois arquivos no diretório de dados privado:
- `accounts.json`: contas IO cadastradas, seus Pokémon ativos e hunts
  declaradas como desbloqueadas.
- `io_hunt_measurements.json`: medições registradas manualmente.

Com `IGA_DATA_DIR` apontando para a pasta privada do projeto original,
é nesse diretório que os arquivos devem estar. Nenhuma cópia de exemplos é
usada automaticamente como medição real.

Exemplo **fictício**, apenas para documentar o formato de uma medição:

```json
[
  {
    "game": "io",
    "profile_id": "meu-perfil",
    "account_id": "minha-conta",
    "pokemon_id": "meu-pokemon-ativo",
    "hunt_id": "hunt-a",
    "minutes": 60,
    "xp_gained": 12000,
    "resources_gained": 10,
    "resources_spent": 2,
    "defeats": 0,
    "source": "manual"
  }
]
```

Os quatro IDs devem corresponder **exatamente** aos itens de `accounts.json`.
São necessários pelo menos **dois IDs de hunts distintos**, ambos com acesso
confirmado e no mínimo **30 minutos de medições** por hunt, sempre com o
mesmo Pokémon ativo. Valores demonstrativos e amostras de outras contas são
ignorados pelo ranking.

Não use o XP atual do treinador como `xp_gained`: preencha o **delta de XP**
realmente ganho durante a medição. Registre recursos ganhos, gastos e
derrotas de forma separada, mesmo que sejam zero.

## Como utilizar

Abra o painel unificado e a seção **Qual hunt rende mais?**.
Alterne entre XP/h, recursos líquidos/h e pontuação equilibrada.

O endpoint GET `/api/io/hunts?objective=xp` fornece a mesma análise com
`configured`, `comparisons` e `identity_verified_live: false`.
Somente `xp`, `resources` e `balanced` são aceitos como objetivo.

As contas declaradas manualmente **não estão automaticamente associadas**
às abas Chrome, porque a extensão ainda não confirma a identidade do
treinador nem a hunt atual. Por isso o comparador não alimenta a fila de
ações executáveis e não altera os modos de automação.

## Fila consultiva

A fila por aba usa HP validado, estado do farm e médias de 5/15 min:
- HP abaixo de 25% gera aviso de revisão manual, **sem Desistir**.
- Farm desconhecido exige confirmação humana, não é interpretado como parado.
- Queda acentuada da média de 5 min ante 15 min solicita investigação;
  **não troca de hunt**.
- Falta de dados pede mais tempo de observação.
- Identidade e hunt permanecem sem confirmação automática.

Cada aviso possui `status: review_only` e `action_authorized: false`.
O servidor não aceita esse aviso como comando nem como aprovação do motor
`io_local_live_controls.py`, que permanece vazio.
