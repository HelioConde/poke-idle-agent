# Idle Game Agent

**Um sistema para Poke Idle IO e Poke Idle World, em um painel único no Windows.**

## INICIAR TUDO (Windows)

**Dê dois cliques em INICIAR-TUDO.bat.** Ele inicia o monitor IO e o painel
integrado juntos em http://127.0.0.1:8768 — sem abrir vários .bat.

    INICIAR-TUDO.bat

Outras opções no MESMO arquivo:

    INICIAR-TUDO.bat --setup
    INICIAR-TUDO.bat --test
    INICIAR-TUDO.bat --check

- `--setup`: cadastra contas e equipes por apelido, sem e-mail/senha.
- `--test`: executa testes Python sem conectar ao jogo.
- `--check`: verifica a estrutura sem abrir o servidor.

O painel carrega automaticamente arquivos privados opcionais da pasta `data/`:
contas, medições de hunts World, capturas sem VIP, IVs e ledger financeiro.
Somente a extensão Chrome do IO precisa ser emparelhada manualmente uma vez,
usando a chave gerada em `data/tab_registry_token.txt` (não compartilhar).

**Poke Idle IO:** observação autorizada e recomendações; execução real
permanece desativada até validar ações específicas. Depois do incidente
`Desistir`, a parada real de farm por esse comando está expressamente bloqueada.

**Poke Idle World:** cálculos PokeGrid e captura sem VIP apenas com dados
anotados manualmente; sem bots externos, autothrow ou coleta de conta.
Gold/diamantes no World não são USDT confirmado.

Os antigos arquivos BAT permanecem só por compatibilidade, mas você não
precisa executá-los. Consulte [guia da inicialização única](docs/INICIAR_TUDO.md).

**Estado:** integração funcional de serviços locais e simuladores testados;
não há comprovação de saques reais nem um bot externo ativado no World.
## Arquitetura universal — contas novas e qualquer Pokémon

**Este agente não é configurado para Charizard 110.** O objetivo é iniciar em
uma conta nova e adaptar a estratégia conforme perfil, treinador, equipe,
Pokémon ativo, hunts realmente desbloqueadas e dados observados.

O motor genérico é **somente consultivo**: World usa medições manuais/offline;
IO usa dados autorizados e gera decisões dry-run. Nenhum clique, login,
comércio ou saque é executado pelo módulo.

### Cadastro guiado de conta no Windows

    py -3 -m app.account_setup

O assistente pergunta o jogo, um apelido local de perfil e conta, nível
do treinador se conhecido, Pokémon de qualquer espécie/nível, Pokémon
ativo e hunts disponíveis. Não informe e-mail, senha ou token. Os registros
ficam em data/accounts.json, arquivo excluído do Git.

### Analisar contas cadastradas

    py -3 -m app.adaptive_strategy --accounts data/accounts.json

### Testar cenários fictícios

    py -3 -m app.adaptive_strategy --accounts examples/adaptive_accounts_demo.json --measurements examples/adaptive_measurements_demo.json

Os exemplos incluem uma conta nova, uma com Charizard 110 e uma conta IO.
São **fictícios**, não comprovam receitas nem experiência no jogo real.
Para comparar hunts reais, forneça JSON de medições por perfil, conta,
jogo, Pokémon e hunt, conforme docs/ARQUITETURA_ADAPTATIVA.md.

Para o objetivo monetário no IO, acrescente evidências de mercado separadas
por jogo, perfil e conta. Elas precisam representar vendas concluídas
comparáveis, sem dados `demo`:

    py -3 -m app.adaptive_strategy --accounts data/accounts.json --objective monetization --market data/minhas_vendas_concluidas.json

O planejador só recomenda revisar uma oportunidade depois que o motor econômico
validar no mínimo três vendas comparáveis. Essa recomendação é dry-run: não
cria anúncios, não compra e não solicita saque.

O módulo `app.financial_ledger.FinancialLedger` mantém em SQLite local, por
conta, os estados `acquired`, `listed`, `sold`, `withdrawal_requested` e
`received`. Apenas `received`, registrado manualmente após confirmação, entra
em `confirmed_usdt_received`; demos, anúncios, Gems e saques pendentes não.
Para exibir uma conta já registrada no painel, sem modificar dados:

    py -3 dashboard.py --ledger data/financial.sqlite3 --finance-game io --finance-profile meu-perfil --finance-account minha-conta

Registre manualmente uma venda concluída (o comando calcula a taxa, mas não
anuncia nem vende nada):

    py -3 -m app.financial_ledger --ledger data/financial.sqlite3 record --game io --profile meu-perfil --account minha-conta --asset "Item" --stage sold --gross-gems 100 --category item

Consulte a conta com `py -3 -m app.financial_ledger --ledger data/financial.sqlite3 summary --game io --profile meu-perfil --account minha-conta`.
O estágio `received` exige `--confirm-received` e só deve ser usado depois de
confirmar manualmente o crédito; nunca informe chave privada ou seed phrase.
## Integração PokeGrid (MIT) — análise offline do World

Incorporamos o cálculo puro de **IVs e projeções de atributos** do
[PokeGrid-source](https://github.com/soufoka/PokeGrid-source), sob MIT,
com os direitos autorais originais preservados em `vendor/pokegrid/LICENSE`.

Também adicionamos relatórios de XP/h, gold líquido/h, kills/h, capturas/h,
suprimentos e shinies, com amostras **manuais** e isolamento por conta,
Pokémon e hunt. O painel recebe um JSON local opcional.

    node tools/pokegrid_iv_cli.js examples/pokegrid_iv_demo.json
    py -3 -m app.world_pokegrid_report --file examples/pokegrid_snapshots_demo.json
    py -3 dashboard.py --world-report examples/pokegrid_snapshots_demo.json

Os exemplos são fictícios e identificados como demo. Para sua análise,
copie-os para `data/` e substitua por dados medidos manualmente.

**Não incluímos o cliente Electron PokeGrid, login automático, 4 contas
conectadas, userscripts nem macros.** As regras do World exigem autorização
prévia da administração para terceiros. Este módulo não se conecta ao jogo.
Não misturamos gold/diamantes World com Gems/USDT do IO.

Guia: [Integração PokeGrid offline](docs/POKEGRID_OFFLINE_INTEGRATION.md).
## Capturas para contas World sem VIP (offline)

Inspirado no projeto [PollitoScripts/Poke-Idle-World-Auto-Catch](https://github.com/PollitoScripts/Poke-Idle-World-Auto-Catch),
criamos um assistente **original e somente manual** para contas sem VIP.
Ele escolhe a prioridade de Pokébolas por conta e tipo de encontro, protege
reservas para shiny, contabiliza tentativas anotadas e recomenda o Auto-Catch
oficial apenas quando a conta informa VIP.

    py -3 -m app.world_capture_assistant --file examples/world_capture_demo.json
    py -3 dashboard.py --world-capture examples/world_capture_demo.json

Os exemplos são fictícios. Para suas contas, use arquivos locais em data/
(nunca envie dados privados ao GitHub). O painel mostra cada conta separada.

**Não instalamos o Tampermonkey nem copiamos o Auto-Catch do PollitoScripts.**
O repositório externo não possui licença explícita; além disso, o Poke Idle
World proíbe autoclickers e extensões sem autorização da equipe. O nosso
módulo não opera o jogo, nem substitui o recurso VIP.

Guia: [Captura manual sem VIP](docs/WORLD_CAPTURE_NONVIP.md).

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
3. Abra chrome://extensions e clique em **Recarregar** na extensão Idle Game Agent (versão 0.2.3).
4. Dê F5 na aba aberta do Poke Idle IO, após salvar seu jogo.
5. Abra o popup da extensão e use **Testar conexão**; depois use **Sincronizar agora**. O popup informa, sem expor a chave, se falta emparelhamento, se a chave foi rejeitada, se o servidor local está inacessível ou se a sincronização foi confirmada.
6. Rode .\OBSERVAR-IO-CHROME.bat no PowerShell.
7. Abra http://127.0.0.1:8768 e aguarde a primeira leitura (até 30s).
8. Observe as novas colunas Nível, XP/h, HP e Decisão simulada.

O diagnóstico também informa o protocolo da leitura. **Leitor desatualizado**
significa que o service worker instalado ainda não envia o protocolo 2; recarregue
a extensão e então a aba `/app`. **Content script desatualizado** significa que
o service worker foi recarregado, mas a página ainda usa o script antigo: recarregue
somente a aba `/app`. Até ambas as versões responderem, o servidor remove XP do
treinador e não calcula XP/h — não há valor estimado ou inventado.

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


### Análise de XP/h por janela (somente leitura)

O monitor IO exibe a taxa curta e médias de 5, 15 e 60 minutos quando
recebe tempo de amostragem suficiente (no mínimo 80% de cada janela).
Não apresenta uma média de 60 min com poucos segundos de dados.
O histórico em RAM é separado por perfil, janela e aba e reiniciado após
troca de nível, redução de XP, troca de barra ou perda de sincronização.
Ainda não existe confirmação automática da identidade do treinador;
por isso essas médias são observações **por aba**, não resultados atribuídos
de forma definitiva a uma conta ou hunt. Várias abas IO aparecem
separadamente na seção de auditoria. Nenhum comando no jogo é executado.

As referências externas estudadas foram Launcher Alt: PokeIdle,
Hunt Atlas e Rebosteio Launcher (detalhes em
`docs/IO_CONTROLS_AUDIT.md`). A extensão não incorpora executores
dessas bibliotecas.
