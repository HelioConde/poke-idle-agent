# Idle Game Agent

**Laboratório independente para Poke Idle World + Poke Idle IO.** Comparador de farm, painel local e protótipo de agente de jogos. Não depende do Brain-SSD.

**Status: MVP demonstrativo.** Os exemplos são fictícios e o agente toma decisões apenas em uma simulação local. Não foram executados bots em contas reais nem confirmados saques.

## Instalar no Windows

Requer Python 3.11+ e Git.

    git clone https://github.com/HelioConde/poke-idle-agent.git
    cd poke-idle-agent
    py -3 -m unittest discover -s tests -v
    py -3 dashboard.py

Abra o painel em http://127.0.0.1:8767 ou clique em INICIAR-PAINEL.bat.

Para testar o agente de demonstração:

    py -3 -m app.agent --steps 20

Outras análises:

    py -3 -m app.lab examples/sessoes_demo.csv
    py -3 -m app.decision examples/hunts_demo.csv

Para importar suas próprias medições, faça uma cópia de examples/sessoes_demo.csv, altere os valores e a coluna source para real, e execute:

    py -3 dashboard.py --csv data/meus_registros.csv

Crie a pasta data, que está no .gitignore. Nunca registre como withdrawn_usd gemas ainda não sacadas, itens anunciados ou vendas pendentes.

## Jogos e permissões

- Poke Idle World (https://poke.idleworld.online/): análise somente leitura / landing pública. Automação externa de contas depende de autorização explícita da equipe (https://poke.idleworld.online/rules).
- Poke Idle IO (https://pokeidle.io/): avaliação de dados e captura passiva. Confirmar os termos atuais (https://pokeidle.io/terms) antes de implementar um agente que interaja com o jogo.

Não há credenciais nem APIs secretas no código.

## Capturar Poke Idle IO sem bloqueio do login Google (Windows)

**Use seu Chrome/Edge normal para o login.** O Google pode bloquear autenticação
em Chromium iniciado pelo Playwright com "este navegador ou app pode não ser seguro".
Não altere o User-Agent e não tente desativar as proteções do Google.

A nova captura padrão usa a janela ativa do Chrome/Edge normal (captura de imagem
na tela do Windows), **sem automação de navegador**, sem inspecionar cookies e sem
capturar telas de login ou outras abas. O sistema ignora janelas que não têm
título do jogo. A barra de endereço é cortada da imagem por padrão.

    py -3 -m pip install -r requirements-desktop.txt
    py -3 -m app.browser_probe --game io --mode desktop --open-browser --seconds 60

Também é possível abrir diretamente \`OBSERVAR-IO-CHROME.bat\`.

Entre no Poke Idle IO manualmente no navegador normal, volte ao terminal e aperte
Enter; então clique na aba do jogo em até quatro segundos. As capturas são
salvas em \`captures/\` (ignorado pelo Git). Se o título da aba não identificar
o jogo, o programa não grava imagens; informe o título exibido na aba.
Para monitores com escala muito alta, use \`--top-crop 150\` ou 180 para garantir
que a barra de endereço fique fora da imagem. Nunca envie capturas de contas
ou informações privadas ao repositório público.

Captura do World pelo navegador comum (apenas observação, sem comandos no jogo):

    py -3 -m app.browser_probe --game world --mode desktop --open-browser --seconds 30

### Playwright: somente páginas públicas, sem login Google

Opcional para testes de layout sem autenticação:

    py -3 -m pip install -r requirements-browser.txt
    py -3 -m playwright install chromium
    py -3 -m app.browser_probe --game io --mode playwright --seconds 30

**Importante:** essas capturas não fazem a IA jogar. O agente que executa
ações continua disponível apenas no ambiente local simulado. Integração
com jogos reais depende das respectivas permissões e de testes separados.

## Projetos usados como referência, não copiados

- https://github.com/allmight-ai/poke-idle-companion (MIT no código autoral; dados do jogo excluídos da licença)
- https://github.com/vineethsaivs/gameagent-ai (MIT, agente baseado em visão e memória)
- https://github.com/undreiss/Idle-Helper (licença restrita; não incorporar código)

O script testar_projetos.ps1 permite clonar e rodar testes offline dos originais sob third_party/ (pasta ignorada). Revisar dependências antes de executá-lo.

## Estrutura

- app/agent.py: simulação local e política de decisão
- app/lab.py: sessões, XP/h e saques realizados
- app/decision.py: pontuação experimental das estratégias de farm
- app/browser_probe.py: captura passiva das telas
- dashboard.py e public/: painel local
- tests/: verificações automatizadas
- docs/: roteiro e referências

## Próximas etapas

Verificar a economia e as permissões dos dois jogos, coletar dados reais com ações permitidas e depois implementar adaptadores isolados, começando pelo IO onde autorizado. Incluir modo dry-run, logs e botão de parada. Antes de afirmar rentabilidade, medir custos e saques efetivamente recebidos.

Licença do código original: MIT. Nenhum resultado financeiro é garantido.
