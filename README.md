<div align="center">
  <h1>🔎 Idle Game Agent</h1>
  <p><strong>Laboratório local para observar métricas de jogos idle e comparar estratégias sem controlar o jogo automaticamente.</strong></p>
  <p><img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white"> <img alt="Status" src="https://img.shields.io/badge/status-prot%C3%B3tipo%20experimental-64748b"></p>
  <p><a href="#come%C3%A7ar-no-windows"><strong>Começar no Windows</strong></a> · <a href="docs/OBJETIVO_PRINCIPAL.md"><strong>Metas e limites</strong></a> · <a href="docs/README_HISTORY_2026-10-25.md"><strong>Histórico técnico</strong></a></p>
</div>

## Objetivo do laboratório

O repositório explora ferramentas de **observação de sessões, análise de métricas e simulação de estratégias** para ambientes como Poke Idle World e Poke Idle IO. A proposta inclui comparar resultados e avaliar decisões com dados verificáveis, respeitando as condições de uso das plataformas.

**Estado real:** MVP experimental. A extensão do navegador tenta obter informações numéricas das páginas, mas **não há comprovação de que todos os seletores funcionem em uma conta autenticada**. Recomendações são em *dry-run*, e o agente não está habilitado para executar ações no jogo.

> Qualquer objetivo econômico presente nos estudos é apenas uma hipótese; **não há garantia de rendimentos, saques ou valorização**. Não automatize interações onde isso viole regras do jogo.

## Componentes

| Diretório / arquivo | Papel |
| --- | --- |
| `dashboard.py` | Painel local de monitoramento |
| `chrome_extension/` | Extensão experimental de observação |
| `app/` | Componentes de aplicação |
| `docs/` | Hipóteses, metas, limites e diagnósticos |
| `examples/` | Exemplos e dados para reproduzir testes |
| `tests/` | Testes automatizados |
| `INICIAR-PAINEL.bat` | Atalho Windows para o painel |

## Começar no Windows

Requer **Python 3.11+** e Git:

```powershell
git clone https://github.com/HelioConde/poke-idle-agent.git
cd poke-idle-agent
py -3 -m unittest discover -s tests -v
py -3 dashboard.py
```

Abra `http://127.0.0.1:8767` para acessar o painel local, conforme o script. Há atalhos Windows para iniciá-lo e coletar métricas, mas revise cada script antes de executar.

## Restrições de operação

- A ferramenta deve **observar** antes de qualquer decisão sobre automação.
- Seletores, capturas e métricas precisam ser validados contra informações reais e autorizadas.
- Resultados do jogo não devem ser apresentados como ganhos financeiros comprovados.
- Não use credenciais privadas em logs, screenshots, arquivos de amostra ou commits.
- Não exponha o dashboard local à internet sem controles de autenticação e acesso.

## Evolução

Próxima prioridade: validar a coleta de métricas com permissão e aferir sua confiabilidade, sem controlar o jogo. Somente depois faz sentido avaliar recomendações e melhorias de UX.

[Documento de objetivos](docs/OBJETIVO_PRINCIPAL.md) · [Histórico e experimentos anteriores](docs/README_HISTORY_2026-10-25.md)

Criado por [Hélio Conde](https://github.com/HelioConde).
