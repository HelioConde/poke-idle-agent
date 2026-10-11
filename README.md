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

## Captura passiva opcional

Instale Playwright e Chromium:

    py -3 -m pip install -r requirements-browser.txt
    py -3 -m playwright install chromium
    py -3 -m app.browser_probe --game world --seconds 30
    py -3 -m app.browser_probe --game io --seconds 60

World: apenas landing pública, navegador isolado sem login. IO: navegador separado, login manual se desejado. Capturas e perfis ficam apenas no computador, excluídos do Git.

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
