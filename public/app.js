async function boot() {
  const status = document.getElementById('data-banner');
  try {
    const response = await fetch('/api/summary', {cache:'no-store'});
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const payload = await response.json();
    const byGame = Object.fromEntries(payload.games.map(item=>[item.game,item]));
    document.querySelectorAll('[data-field]').forEach(el=>{
      const [game, field] = el.dataset.field.split(':');
      const value = byGame[game]?.[field];
      if (value === undefined || value === null) {
        el.textContent = 'Sem dados';
      } else if (field === 'withdrawn_usd') {
        el.textContent = Number(value).toLocaleString('pt-BR',{style:'currency',currency:'USD'});
      } else {
        el.textContent = Number(value).toLocaleString('pt-BR',{maximumFractionDigits:2});
      }
    });
    status.textContent = payload.sample
      ? 'DADOS FICTÍCIOS · Exemplo de funcionamento (' + payload.source_file + ')'
      : 'DADOS REGISTRADOS · Arquivo: ' + payload.source_file + ' — saques requerem comprovação.';
  } catch (error) {
    status.textContent = 'Não foi possível carregar os dados: ' + error.message;
  }
}
async function loadFinance() {
  const status = document.getElementById('finance-banner');
  try {
    const response = await fetch('/api/finance', {cache:'no-store'});
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const payload = await response.json();
    if (!payload.configured) {
      status.textContent = 'Sem conta financeira configurada. ' + payload.reason;
      return;
    }
    const summary = payload.summary;
    document.querySelectorAll('[data-finance]').forEach(el => {
      const field = el.dataset.finance;
      const value = summary[field];
      el.textContent = field.includes('usdt')
        ? Number(value).toLocaleString('pt-BR',{style:'currency',currency:'USD'})
        : Number(value).toLocaleString('pt-BR',{maximumFractionDigits:2});
    });
    status.textContent = summary.real_revenue_confirmed
      ? 'Recebimento informado manualmente; confira a origem antes de tratar como resultado final.'
      : 'Nenhum USDT confirmado nesta conta. Gems, anúncios e saques pendentes permanecem fora da receita real.';
  } catch (error) {
    status.textContent = 'Não foi possível carregar o livro-caixa: ' + error.message;
  }
}
boot();
loadFinance();
