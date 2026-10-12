# Idle Game Agent — UM INICIALIZADOR PARA TUDO

## Uso principal (Windows)

Duplo clique em **INICIAR-TUDO.bat**.

O arquivo:
- encontra Python 3 instalado (py -3, com fallback para python);
- executa um processo Python com o painel e o registro de abas;
- disponibiliza tudo em **http://127.0.0.1:8768**;
- abre o navegador automaticamente;
- mantém a janela do terminal (Ctrl+C encerra o servidor);
- não inicia bots de gameplay, login, evolução, compra ou saque.

O primeiro uso da extensão IO exige configurar manualmente UMA VEZ:
1. No Chrome, abra chrome://extensions, ative modo desenvolvedor e carregue **chrome_extension/**.
2. Abra as opções da extensão e emparelhe com a chave local em **data/tab_registry_token.txt**. Nunca compartilhe essa chave no chat, GitHub ou prints.
3. Abra o jogo IO numa aba normalmente autenticada.
4. As abas IO sincronizadas aparecem na Central de controle e no monitor detalhado, ambos na porta 8768.

Não instale a extensão no World para capturar dados privados. Ela só identifica título e presença de abas World.

### Comandos do mesmo BAT

    INICIAR-TUDO.bat
    INICIAR-TUDO.bat --setup
    INICIAR-TUDO.bat --test
    INICIAR-TUDO.bat --check
    INICIAR-TUDO.bat --help

- --setup: cadastrar apelidos locais de contas e times, sem login/senha.
- --test: regressões Python, sem abrir o jogo. Node é validado no GitHub Actions.
- --check: checar arquivos de entrada sem iniciar servidor.
- --help: mostrar os comandos.

Não é necessário abrir INICIAR-MONITOR-ABAS.bat, INICIAR-PAINEL.bat ou OBSERVAR-IO-CHROME.bat separadamente. Eles foram mantidos como atalhos legados de compatibilidade.

### Conteúdo integrado na tela única

| Seção | Origem | Uso |
|---|---|---|
| Contas/equipe | data/accounts.json | Cadastro via --setup |
| Monitor Chrome IO | Extensão + /api/sync | Métricas autorizadas e sugestões dry-run |
| Monitor detalhado | /monitor | Abas ativas/inativas e diagnóstico |
| PokeGrid World | data/world_snapshots.json | XP, gold e suprimentos, anotações manuais |
| Captura sem VIP | data/world_capture.json | Prioridades e reservas de Pokébolas, sem autothrow |
| IVs PokeGrid | data/world_ivs.json | Cálculo local Node opcional |
| Livro-caixa | data/financial.sqlite3 | Selecionar conta IO cadastrada, somente leitura |

Os arquivos em data/ são privados e ignorados pelo Git. Não envie cookies, senhas, chaves, dados de carteiras ou identificadores sensíveis.

## Configurar World

Cadastro básico:

    INICIAR-TUDO.bat --setup

Configuração manual dos relatórios opcionais:

    if not exist data mkdir data
    copy examples\pokegrid_snapshots_demo.json data\world_snapshots.json
    copy examples\world_capture_demo.json data\world_capture.json
    copy examples\pokegrid_iv_demo.json data\world_ivs.json

Edite esses arquivos com seus dados reais digitados manualmente, alterando source de demo para manual apenas quando forem medições verdadeiras. Node.js é opcional somente para IVs. Depois execute INICIAR-TUDO.bat; os arquivos existentes são carregados automaticamente.

## Economia e segurança

A extensão IO mostra leituras de HUD na rota permitida; o inicializador não executa ações no jogo. No financeiro, selecione uma conta IO cadastrada. Nenhuma conta do World pode ter USDT presumido. Somente saque manual comprovado entra como dinheiro recebido.

O executor IO continua protegido pelo incidente Desistir: o modo live stop_farm está bloqueado. Não use Desistir como pausa do farm.

No World, scripts e autoclickers externos sem autorização são proibidos. PokeGrid e assistente sem VIP funcionam offline/manual, não como bypass VIP.

## Diagnóstico

- Porta 8768 ocupada: feche o antigo monitor de abas e tente novamente. O iniciador não mata outros processos.
- BAT não abre: rode INICIAR-TUDO.bat --check; confirme Python 3.11+ instalado.
- Extensão não aparece: confira extensão, chave local, rota /app e emparelhamento.
- Contas não aparecem: use INICIAR-TUDO.bat --setup e recarregue o painel.
- World sem métricas: crie arquivos manuais em data/; sem medições, aparecerá ausência de dados.
- IVs indisponíveis: instale Node.js caso queira projeções; os demais módulos não dependem dele.
- Exemplo fictício: banners deixam explícito que é demo e não entra em renda real.

## Git e branches

Branch: feat/unified-one-click-launcher; deriva de feat/world-nonvip-capture-assistant, que incorpora módulos PokeGrid, segurança IO, executor simulado, motor adaptativo e ledger remoto.

Não foram feitos reset, force-push ou merge automático em main. Commits econômicos locais não publicados e o antigo planejador independente continuam intactos. Só realizar merge após revisar o ambiente local.
