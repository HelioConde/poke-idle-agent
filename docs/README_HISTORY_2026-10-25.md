# Histórico da documentação — poke-idle-agent

> README anterior preservado em 25/10/2026 durante a modernização da página principal. Para a versão mais clara, consulte [README](../README.md).

---

# Idle Game Agent — Laboratório de observação e análise

**Projeto experimental para observar dados de jogos idle, comparar estratégias e estudar possíveis automações com limites claros.**

**Escopo atual descrito:** painel local, observação de métricas e recomendações em modo de simulação. O agente não deve ser tratado como um robô validado para controle automático.

> Resultados econômicos, vendas e saques não são garantidos. Respeite as regras do jogo e evite automações não autorizadas. Leia as permissões e limitações antes de testar.

---

**Laboratório independente para Poke Idle World + Poke Idle IO.** Comparador de farm, painel local e protótipo de agente de jogos. Não depende do Brain-SSD.

**Status: MVP experimental.** A extensão já tenta observar métricas numéricas reais no IO, mas os seletores ainda não foram validados em uma conta autenticada. As recomendações são dry-run; o agente ainda não controla o jogo. Nenhum saque real foi confirmado.

## Objetivo principal: transformar farm em USDT comprovado

A missão do agente é **maximizar o valor líquido realizável em USDT por hora**,
por meio de vendas legítimas no Mercado da Comunidade do Poke Idle IO.
**XP e nível são meios para liberar hunts e criar itens ou Pokémon vendáveis,
não a finalidade da automação.** Primeira meta experimental: obter 1.000 Gems
líquidas de vendas concluídas e validar manualmente um saque de US$ 7,
sem investir na compra de Gems e sem prometer lucros.

Leia a [estratégia principal, metas, regras e métricas](docs/OBJETIVO_PRINCIPAL.md).
Esse documento deve orientar decisões do agente, desenvolvimento e testes.

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

## Evolução v0.2 — observar o Poke Idle IO sem trocar de aba

Inspirado no **Poke Idle Companion** (métricas reais de sessão) e no
**GameAgent AI** (ciclo observar → decidir → agir → verificar).
A implementação desta etapa é original; não incorporamos código do Idle Helper,
que possui licença restritiva.

A extensão agora tenta ler indicadores numéricos **já visíveis no HTML**
do Poke Idle IO: nível, XP atual, XP alvo, HP, Coins e Gems. A aba pode estar
inativa; não é necessário clicar nela. No serviço local os valores são
validados antes de calcular o XP/h entre duas amostras do mesmo nível.
O painel exibe uma sugestão de ação em **dry-run**, que nunca clica no jogo.

**Primeiro uso após atualizar:**

1. Pare o monitor no terminal com Ctrl+C.
2. Rode git pull origin main.
3. Abra chrome://extensions e clique em **Recarregar** na extensão Idle Game Agent.
4. Dê F5 na aba aberta do Poke Idle IO, após salvar seu jogo.
5. Rode .\OBSERVAR-IO-CHROME.bat no PowerShell.
6. Abra http://127.0.0.1:8768 e aguarde a primeira leitura (até 30s).
7. Observe as novas colunas Nível, XP/h, HP e Decisão simulada.

**Se os dados não aparecerem:** isso NÃO prova defeito de login nem que a
IA esteja jogando. O jogo pode desenhar seu HUD no Canvas, ou usar marcações
de HTML que ainda não conhecemos. A primeira integração aceita somente
rótulos numéricos conservadores, não lê HTML livre, chat, inputs, credenciais,
WebSocket ou localStorage. Não inclui decisões com dinheiro real.

Validação dos testes:

    py -3 -m unittest discover -s tests -v
    node tests/test_extension_rules.js
    node tests/test_io_dom.js

Detalhes de arquitetura, limitações e referências:
[docs/ARQUITETURA_AGENT.md](docs/ARQUITETURA_AGENT.md).

## Monitorar TODAS as abas, inclusive inativas (novo modo recomendado)

Este modo corrige a limitação do Windows: o título da janela comum mostra apenas
a aba selecionada. A extensão do Chrome acessa a lista de abas dos **dois jogos**,
incluindo abas inativas, sem mover o foco e sem exigir uma janela separada.
O programa usa **URL e título da aba**, não procura o título da janela do Windows.

1. Atualize com git pull origin main.
2. Execute OBSERVAR-IO-CHROME.bat (agora inicia o monitor de abas) ou
   INICIAR-MONITOR-ABAS.bat.
3. No terminal aparece a **CHAVE DE EMPARELHAMENTO**. Mantenha-a privada.
4. No Chrome normal, abra chrome://extensions, ative "Modo do desenvolvedor",
   selecione "Carregar sem compactação" e escolha a pasta chrome_extension
   dentro deste repositório.
5. Clique no ícone do Idle Game Agent, informe um nome de perfil e cole a chave.
6. Clique "Salvar e sincronizar"; abra http://127.0.0.1:8768.
7. Abra pokeidle.io normalmente e mude para outra aba: ele continua aparecendo
   como INATIVO no painel. Para um segundo perfil Chrome, instale a mesma
   extensão nesse perfil e repita o passo 5 com um nome diferente.

**O que ele faz:** lista abas por jogo, título, perfil, janela e se estão
selecionadas. Detecta múltiplas abas e perfis, sem login automatizado, sem
acesso a cookies, senhas ou conteúdo de páginas. Todos os dados enviados pela
extensão são somente metadados dos domínios dos jogos, para 127.0.0.1.
A chave fica no computador e no armazenamento local da extensão. O monitor
remove perfis desatualizados após dois minutos sem sincronização.

**O que ele NÃO faz:** capturar vídeo ou screenshots de abas inativas, controlar
personagens, iniciar sessão ou gerenciar várias contas automaticamente.
A API de captura visível do Chrome só captura a aba selecionada; para
observação visual de abas ocultas será preciso estudar outra abordagem,
com permissões adequadas e os limites de renderização em segundo plano.

Várias abas no mesmo perfil geralmente compartilham a mesma sessão de login.
Para contas separadas, use perfis distintos **somente se as regras dos jogos
permitirem múltiplas contas**. A permissão para multi-contas ainda não foi
confirmada e não implementamos sua automação.

Os antigos comandos com imagens foram preservados, mas têm limitações:

    OBSERVAR-IO-CHROME.bat --capturas

Para executar o antigo capturador de janelas de forma direta:

    py -3 -m app.browser_probe --game io --mode window --seconds 60

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

## Diagnóstico de leitura IO (v0.3)

O site https://pokeidle.io/ é a página de apresentação. Para abrir o jogo,
use https://pokeidle.io/app, faça login e selecione uma hunt manualmente.
Nosso adaptador apenas lê indicadores do DOM da aba /app e não confunde
propagandas da página inicial com XP/Coins/Gems da sua conta.

Atualize com git pull origin main, recarregue a extensão em chrome://extensions,
recarregue a aba /app com F5 e reinicie .\\OBSERVAR-IO-CHROME.bat.
Se as métricas forem vazias, a coluna **Diagnóstico** diferenciará:

- Página inicial — navegue até /app.
- Leitor não respondeu — recarregue extensão e jogo, confira se a página terminou de carregar.
- DOM acessado, mas sem indicadores — exibe apenas as contagens de canvas/iframe/elementos; não copia HTML ou informações privadas.
- Métricas reconhecidas — números extraídos que ainda precisam ser conferidos contra o HUD real.

Mesmo quando detecta Canvas, o coletor ainda não lê pixels de abas inativas
nem opera a interface do jogo. Não publique capturas com dados privados.
