# Executor de automações do Poke Idle IO

## Implementado e não implementado

Esta branch adiciona motor de PROPOSTAS, dry-run, SIMULAÇÃO local,
limites financeiros, confirmação de uso único, validação de estado antes e
depois, isolamento de contas, pausa e parada de emergência.

**Nenhum adaptador de Chrome autenticado foi criado nem ativado.** Os
testes provam o comportamento do simulador, não que uma ação foi realizada
no Poke Idle IO. O modo real permanece indisponível enquanto controles,
permissões e verificação da interface não forem testados pelo usuário.

Poke Idle IO permite automação em jogo e no Market segundo os termos atuais:
https://pokeidle.io/terms. O World não permite automação externa sem a
autorização expressa da equipe: https://poke.idleworld.online/rules.

## Operações abrangidas pelo planejador

- **Melhor mapa:** escolher hunt desbloqueada com XP/h ou recursos líquidos/h
  medidos em duas hunts (mínimo 30 minutos cada) para a conta e Pokémon atuais.
  Para recomendação monetária, exigir dados REAIS de vendas concluídas e
  integração com o motor econômico preservado nos commits locais.
- **Iniciar e parar farm:** só quando o estado é conhecido; parar antes de
  trocar mapa. Se HP cair abaixo de 25%, priorizar parada e recuperação.
- **Inventário:** propor leitura segura, identificar ativos e estoque.
- **Pokémon:** propor inspeção; evolução só se elegibilidade e custos estiverem
  confirmados. Evolução efetiva exige confirmação humana específica.
- **Anúncio:** rascunho separado de publicação. Publicar não gera receita.
  Requer estoque, negociabilidade, preço validado, benefício líquido positivo
  e no mínimo três vendas concluídas comparáveis.
- **Compra de item/Pokémon:** apenas oportunidade validada, com limite de gasto,
  saldo e confirmação explícita de valor, quantidade e conta.
- **Vender ao NPC e cancelar anúncio:** suportados no simulador, com verificação
  de alteração exata do inventário/anúncio.
- **Login, CAPTCHA, depósitos, compra de moeda, saques e transferência entre
  contas:** não implementados e sem permissão de execução.

## Proteções

1. Modo dry_run é o padrão e nunca chama um driver.
2. simulation aceita somente o adaptador fictício de memória.
3. live exige um adaptador real futuro cuja ação esteja individualmente
   verificada e um consentimento de uso único vinculado ao pedido completo.
4. ApprovalRegistry.issue deve ser disparado SOMENTE após gesto explícito do
   usuário no painel ou console, nunca por IA, página web ou telemetria.
5. A política padrão tem teto ZERO para compras e anúncios com Gems.
6. A conta/perfil observados devem corresponder exatamente à requisição.
7. Seleção de mapa exige farm parado; início exige mapa conhecido.
8. Compras e anúncios verificam quantidade exata e diferença de saldo.
9. Incerteza ou erro após acionar o adaptador causa parada de emergência.
10. Não reutilizar request_id já concluído.

## Como testar agora

No Windows PowerShell, na raiz da branch:

    py -3 -m app.io_action_engine
    py -3 -m unittest discover -s tests -v

O primeiro comando executa somente seis ações fictícias e retorna registros
com status simulated: selecionar hunt, começar farm, inspecionar inventário,
anunciar item, comprar item e interromper farm.

## Bloqueio antes de ações reais

A primeira operação REAL precisa ser seleção de mapa no navegador
autenticado, com intervenção humana e logs sanitizados. Antes disso:

1. Capturar e documentar o layout autorizado do jogo IO na rota /app.
2. Identificar seletores estáveis do mapa, inventário, menus e farm.
3. Se a interface usar Canvas, desenvolver adaptador próprio e verificar
   quadro anterior/posterior. Não supor que Chrome produz quadros de abas
   suspensas ou minimizadas.
4. Criar driver por ação com escopo mínimo e timeout, sem ler credenciais
   ou usar APIs ocultas/endpoints não autorizados.
5. Validar seleção de mapa e start/stop com confirmação e parada, então
   realizar testes de inventário, evolução, anúncios e compras separadamente.
6. Reconciliar a branch econômica local antes de usar Gems e preços reais.

## Divergência financeira oficial

A página inicial do IO anuncia 10% de comissão em Coins; os termos
revisados em 30/09/2026 apresentam 15% para Gold. Não realizar cálculo
financeiro nem publicar em Coins automaticamente até conferir no modal
autenticado qual taxa se aplica.

Os 15% de itens vendidos por Gems e as taxas progressivas de Pokémon
estão descritos nos termos, mas ainda exigem conferência antes de liberar
a operação. Anúncio não é venda; Gems em saldo não são USDT confirmado.

## Estrutura

- app/io_action_engine.py: execução, aprovações, verificações e simulador.
- app/io_operation_planner.py: decisão por evidência, mapa, farm e mercado.
- tests/test_io_action_engine.py: segurança e ações isoladas.
- tests/test_io_operation_planner.py: seleção de hunt, evolução e demanda.
- tests/test_io_operator_flow.py: fluxo integrado no simulador.

Trabalhe sempre numa worktree separada e preserve os commits locais de
motor econômico até validar o merge manual.
