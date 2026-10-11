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
boot();
