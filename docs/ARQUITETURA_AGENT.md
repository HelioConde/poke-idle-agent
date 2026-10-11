# Idle Game Agent — coleta real de IO + agente em simulação

## Referências reaproveitadas na arquitetura

- [Poke Idle Companion](https://github.com/allmight-ai/poke-idle-companion)
  (MIT para o código dos autores): medição de XP por janela de observação,
  resumos estatísticos e distinção entre medidas e estimativas. O projeto
  é para *Poke Idle World*, tem autorização de coleta declarada e não
  controla o jogo. **Não copiamos dados ou hooks de WebSocket do World**.
- [GameAgent AI](https://github.com/vineethsaivs/gameagent-ai) (MIT): organização
  em adapter / observe / decide / act / verify / memory. Nosso primeiro adaptador
  é IO por DOM e a etapa ACT está desabilitada em jogos reais.
- [Idle Helper](https://github.com/undreiss/Idle-Helper): licença restritiva.
  Apenas inspiração conceitual; nenhum arquivo ou algoritmo foi incorporado.

## Pipeline real (v0.2)

1. Extensão Manifest V3 monitora todas as abas abertas nos domínios dos jogos.
2. Content script em pokeidle.io tenta reconhecer **somente rótulos e números do
   DOM**: nível, XP, HP, Coins e Gems. Não lê localStorage, cookies, inputs,
   comunicação em rede, URL de sessão ou textos livres/chat. Nunca intercepta
   fetch ou WebSocket e nunca chama o servidor do jogo.
3. Service worker pede um snapshot a cada sincronização. Abas inativas
   podem ser lidas se Chrome executar o content script; a aba não recebe foco.
4. Envia somente métricas numéricas para o serviço local (127.0.0.1:8768)
   autenticado por chave de emparelhamento.
5. Backend valida esquema e limites, mede XP/h entre leituras no mesmo nível
   e prepara recomendações **dry-run**.
6. Painel exibe níveis, HP, XP/h medido, ausência de dados e sugestão.
7. Nenhum clique é executado no jogo. Nenhuma compra, venda, transação,
   saque ou automação de múltiplas contas.

## Limitações importantes

- O HTML da versão autenticada do IO não foi inspecionado; os padrões atuais
  de texto são heurísticos e podem não reconhecer o HUD real. Se o jogo renderizar
  o HUD em canvas, a coleta DOM retornará vazio — sem forjar números.
- Chrome pode reduzir/suspender timers e renderização de abas inativas. A medição
  de XP/h depende de amostras com intervalo suficiente e não deve ser considerada
  exata se o jogo pausa em segundo plano.
- World continua **somente metadados da aba**, sem coleta dentro do jogo
  ou automação de conta.
- A extensão observa apenas os domínios declarados no manifesto.
- Múltiplos perfis são distinguidos, não se presume que multi-account seja permitido.
- Dados como gemas não representam receita: apenas saques efetivamente
  recebidos são dinheiro. Os termos do IO permitem automação, mas proíbem
  fraude e manipulação da economia.

## Próxima etapa — verificação em conta real

O usuário deve atualizar o repositório, recarregar a extensão em
chrome://extensions e recarregar a aba do jogo. Se tudo aparecer como
"Sem estatísticas legíveis no DOM", precisaremos de uma captura privada do
HUD e/ou evidência de seletores de elementos do jogo para desenvolver um
adaptador preciso. Não publique token, e-mail, CPF, dados de conta ou wallet.

Após validar leituras e permissões, implementar uma lista explícita de ações
autorizadas, um executor em sandbox com dry-run obrigatório, confirmação
manual em operações de risco, parada e limites de frequência — sem cópias
de código com licença incompatível.
