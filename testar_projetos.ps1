# Executa testes de repositórios externos isoladamente; não roda bots nos jogos.
param([switch]$IncluirGameAgent)
$ErrorActionPreference = 'Stop'
$base = Join-Path $PSScriptRoot 'third_party'
New-Item -ItemType Directory -Force -Path $base | Out-Null
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git nao encontrado.' }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js nao encontrado.' }
$companion = Join-Path $base 'poke-idle-companion'
if (-not (Test-Path $companion)) {
    git clone --depth 1 https://github.com/allmight-ai/poke-idle-companion.git $companion
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao clonar Companion.' }
}
Push-Location (Join-Path $companion 'extension/tests')
try {
    node teste.js; if ($LASTEXITCODE -ne 0) { throw 'Teste Companion falhou.' }
    node breeding-teste.js; if ($LASTEXITCODE -ne 0) { throw 'Teste breeding falhou.' }
} finally { Pop-Location }
if ($IncluirGameAgent) {
    $agent = Join-Path $base 'gameagent-ai'
    if (-not (Test-Path $agent)) {
        git clone --depth 1 https://github.com/vineethsaivs/gameagent-ai.git $agent
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao clonar GameAgent.' }
    }
    Push-Location $agent
    try {
        py -3 -m pip install -e '.[dev]'
        if ($LASTEXITCODE -ne 0) { throw 'Erro instalando dependencias GameAgent.' }
        py -3 -m pytest tests/ -v
        if ($LASTEXITCODE -ne 0) { throw 'Testes GameAgent falharam.' }
    } finally { Pop-Location }
}
Write-Host 'Testes offline terminados.' -ForegroundColor Green
