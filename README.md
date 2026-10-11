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

## Captura do Poke Idle IO em segundo plano (Chrome normal)

**Não precisa deixar o Chrome focado.** Abra https://pokeidle.io/ em
uma **janela separada** do Chrome/Edge normal, faça login manualmente e deixe
a aba do jogo selecionada nessa janela. Pode colocar qualquer outro programa
na frente; o observador localiza a janela mesmo sem foco.

**Não minimize a janela.** Em Windows o Chrome pode deixar de renderizar
janelas minimizadas; algumas combinações de Chrome/GPU também podem gerar
quadros vazios ou congelados quando a janela está completamente coberta.
A captura em segundo plano usa a API PrintWindow (tentativa, sem garantia
de compatibilidade com todas as versões de Chrome). Não lê cookies/senhas
e não usa Playwright para autenticação.

Abra o script no Windows:

    OBSERVAR-IO-CHROME.bat

Ou execute:

    py -3 -m pip install -r requirements-desktop.txt
    py -3 -m app.browser_probe --game io --mode window --seconds 60 --interval 10

Quando solicitar, pressione Enter após concluir o login. **Depois pode usar
outros programas livremente**, desde que não minimize a janela do jogo.
Imagens ficam em captures/, excluídas do GitHub. O sistema corta a barra
de endereço da imagem (use --top-crop 150 se sua barra for mais alta).

Se o programa não localizar o jogo, confirme que a **aba selecionada dessa
janela separada** é o Poke Idle IO. Se capturas ficarem pretas ou congeladas,
o próximo método recomendado é Windows Graphics Capture (por exemplo,
OBS Studio com fonte Captura de Janela). A alternativa legada --mode desktop
só funciona quando a janela está em primeiro plano.

World, somente observação permitida:

    py -3 -m app.browser_probe --game world --mode window --seconds 30

Não há automação de ações em contas nem comprovação de saques.

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
