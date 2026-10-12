# Referências e licenças

Este repositório é código original sob MIT, não um fork e não distribui terceiros.

- Poke Idle Companion: https://github.com/allmight-ai/poke-idle-companion — analytics, XP/h, breeding, testes. MIT apenas para código original; dados de jogo pertencem aos detentores dos direitos.
- GameAgent AI: https://github.com/vineethsaivs/gameagent-ai — visão, browser, loop observe/decide/act/learn, SQLite. MIT. Atenção ao custo de modelos de visão.
- Idle Helper: https://github.com/undreiss/Idle-Helper — automação de rotinas estudada conceitualmente. Licença personalizada que restringe redistribuição, modificações e comercialização; NÃO incorporamos seu código.

O script testar_projetos.ps1 baixa cópias externas em third_party/ somente para testes separados. Licenças dos repositórios externos continuam se aplicando.

## Verificação mais recente

Em 2026-10-11, `testar_projetos.ps1` executou com sucesso 90 verificações do
coletor/combate/recomendação e 24 de breeding do Companion. A única adaptação
no projeto foi uma implementação Python original da ideia de separar duração de
combate e espera de respawn; não importamos código, dados de jogo, WebSocket,
tokens ou automação do World.
