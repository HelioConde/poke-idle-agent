# Objetivo principal: renda real comprovada com farm eficiente no Poke Idle IO

Pesquisa e definição: 11/10/2026. Fontes oficiais:
- https://pokeidle.io/
- https://pokeidle.io/terms
Contexto de comunidade (relatos promocionais, não provas independentes de saque):
- https://www.sotwe.com/pokeidleio?lang=en
- https://www.sotwe.com/befoin?lang=tr

## Missão

**Maximizar o valor líquido, realizável e comprovável em USDT por hora de operação,
vendendo legitimamente Pokémon e itens obtidos jogando no Mercado da Comunidade,
sem depender de compra de Gems e sem privilegiar XP que não aumente a capacidade
de produzir itens desejados por compradores.**

A primeira meta experimental é **obter 1.000 Gems líquidas de vendas concluídas**
e **validar manualmente um saque de US$ 7 em USDT** na rede Solana, sem concluir
que isso representa lucro até descontar custos. O projeto não promete receitas.

**Gems não vêm de loot nem quests:** entram no jogo por compras e são recebidas
de outros jogadores via vendas no mercado. Anúncios não são vendas, valores
de listagem não são preço efetivo e Gems em conta não são USDT recebido.

## Critério principal da IA

Ordenar estratégias pelo **USDT líquido realizado por hora** em janelas de
observação suficientemente longas, descontando custos operacionais verificáveis.
Na ausência de vendas suficientes, usar como **indicador provisório claramente
rotulado** o valor esperado líquido em Gems/h (preço REAL de vendas comparáveis,
não apenas anúncios) multiplicado por probabilidade de obtenção, probabilidade
de venda, taxa de mercado e confiança da medição.

Indicadores secundários: tempo por caça, capturas bem-sucedidas/h, raridade,
P5/shiny, vendas concluídas, demanda, liquidez, sobrevida, itens por hora,
consumo de recursos, XP/h, nível de treinador e eficiência do Pokémon.

**Não otimizar XP/h cegamente.** Upar é um investimento e deve ser priorizado
quando permitir acesso a hunts melhores, melhorar a sobrevivência ou criar
Pokémon negociáveis.

## Caminhos de geração de valor

1. **Pokémon vendáveis:** a vitrine aceita Pokémon comuns com pelo menos
   nível 50 e nota 3,5; shiny e P5 são exceções e podem ser anunciados em
   qualquer nível. Estudar demanda real antes de investir em treinamento.
2. **Shiny e P5:** raros, de alto potencial, mas extremamente variáveis.
   O shiny é 1/24.000 *por captura bem-sucedida*, não por encontro. O
   P5 tem chance oficial de 0,005% por captura. Nenhum é renda previsível.
3. **Itens raros:** boss tokens, fragmentos e peças de TM, Shiny Stone,
   casa ou bicicleta rara; verificar primeiro o que é obtível no nível atual,
   negociável e realmente vendido.
4. **Progressão para acesso:** Outland a partir do nível 150 de treinador;
   avaliar quantitativamente se perseguir esse marco aumenta a renda
   potencial. Não exigir nível 150 para tentar a primeira venda.
5. **Hunts eficientes:** combater onde há melhor retorno em itens
   negociáveis após tempo, falhas e recursos. Aproveitar análise de hunts e
   rotinas automáticas já oferecidas pelo próprio jogo.

## Plano de metas

**Etapa A — instrumentação (sem dinheiro):**
- Fazer leitor do IO reconhecer conta, rota /app, nível e estado da hunt.
- Medir ao menos 3 hunts comparáveis com horário, duração, capturas,
  recompensas e custos, ou registrar claramente a falta de dados.
- Ler preços e histórico de negócios por meios permitidos, sem operar o mercado.
- Nunca transformar exemplos/sessoes_demo.csv em prova real.

**Etapa B — primeiro ativo comercializável:**
- Selecionar item/Pokémon cujo histórico indique demanda.
- Priorizar evolução de um Pokémon para nível 50/nota 3,5 se comprovadamente
  mais econômico que farmar itens raros; se shiny/P5 aparecer, proteger.
- Calcular preço mínimo e taxas para obter Gems líquidas; **não vender itens
  irreversivelmente sem confirmação explícita**.

**Etapa C — primeira conversão:**
- Obter a primeira venda concluída em Gems no mercado oficial.
- Acumular pelo menos 1.000 Gems **líquidas** e de proveniência legítima.
- Validar manualmente o processo de saque e o crédito recebido em USDT;
  nada de transferências ou saques automáticos.

**Etapa D — otimização em 30 dias:**
- Medir horas, gastos, vendas concluídas e USDT realmente recebido.
- Priorizar estratégia com maior retorno líquido, com incerteza e intervalo
  de confiança; deixar explícito quando amostragem não é suficiente.
- Escolher entre upar treinador, upar Pokémon negociáveis, farmar itens ou
  preservar a hunt atual pela relação custo/oportunidade.

## Regras financeiras confirmadas no site oficial

- Preço de recompra no saque: **US$ 0,007 por Gem**.
- Saque mínimo: **1.000 Gems = US$ 7**.
- Gem comprada custa **US$ 0,01**; não usar preço de compra como receita
  líquida do vendedor.
- Taxa de venda de itens e diamantes por Gems: **15%**.
- Taxa de venda de Pokémon por Gems: tabela progressiva, conforme os termos
  vigentes (13% até 500; 10% de 501 a 5.000; 7,5% acima). Implementar
  cálculo segmentado e testes antes de utilizar em decisões.
- Vendas em gold/Coins, embora úteis para financiar o farm, não equivalem
  a Gems sacáveis.
- A negociação deve ocorrer **somente dentro do Community Market**.
- Riscos: iliquidez, preços mutáveis, falha de saques, regras mutáveis,
  encerramento do servidor, custos e tributação aplicável.

## Restrições de execução

- IO: permissões de automação conforme termos, mas nunca burlar autenticação,
  manipular mercado, vender fora do mercado, coordenar contas para transferir
  valor artificialmente ou realizar operações financeiras sem confirmação.
- World: manter somente análise/automações oficiais e recursos externos
  expressamente autorizados; não usar bots externos.
- Perfis: não assumir que uso de várias contas está autorizado.
- O executor deve começar em **dry-run**, com log de todas as sugestões,
  explicações, limites de risco e parada de emergência.
- Resultado financeiro válido significa USDT creditado e verificável em
  carteira, não Gems estimadas, itens anunciados ou alegações promocionais.

## Requisitos para o Copilot

Todas as funcionalidades propostas em app/decision.py, app/lab.py, agentes
e painel devem usar este arquivo como **fonte de verdade do objetivo**.
Criar testes de ranking que garantam:
- Hunt com mais XP não ganha se sua renda realizável por hora é menor.
- Hunt com item caro mas sem liquidez comprovada não é declarada lucrativa.
- Gastos em Coins e dinheiro real são contabilizados separadamente.
- Saques não comprovados não aparecem como receita.
- Sem histórico suficiente, recomenda-se medir mais, não comprar itens.
- Mundo World nunca recebe comandos de automação externa proibidos.

Nunca declarar automação financeira pronta apenas por simulação.
