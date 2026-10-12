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

async function loadWorldPokeGrid() {
  const status = document.getElementById('world-companion-banner');
  const container = document.getElementById('world-companion-results');
  if (!status || !container) return;
  container.replaceChildren();
  try {
    const response = await fetch('/api/world-pokegrid', {cache:'no-store'});
    if (!response.ok) throw new Error('HTTP '+response.status);
    const payload = await response.json();
    if (!payload.configured) {
      status.textContent = 'Nenhum relatório manual configurado. Abra o painel com --world-report data/world_snapshots.json';
      return;
    }
    const report = payload.report;
    status.textContent = report.is_demo
      ? 'DADOS FICTÍCIOS — demonstração, sem conexão ao jogo e sem rendimentos reais.'
      : 'ANOTAÇÕES MANUAIS — confira os valores; nenhuma ação automática é executada.';
    if (!report.groups.length) {
      const p=document.createElement('p'); p.textContent='Nenhuma medição cadastrada.';
      container.appendChild(p); return;
    }
    for (const entry of report.groups.slice(0,40)) {
      const card=document.createElement('article');
      card.className='world-sample';
      const heading=document.createElement('strong');
      heading.textContent=entry.account_id+' · '+entry.pokemon_id+' · '+entry.hunt_id;
      card.appendChild(heading);
      const body=document.createElement('p');
      body.textContent=entry.status==='measured'
        ? 'XP/h: '+entry.xp_per_hour.toLocaleString('pt-BR')+
          ' · Gold líquido/h: '+entry.net_gold_per_hour.toLocaleString('pt-BR')+
          ' · Abates/h: '+entry.kills_per_hour.toLocaleString('pt-BR')+
          ' · Capturas/h: '+entry.captures_per_hour.toLocaleString('pt-BR')
        : entry.status+': '+entry.reason;
      card.appendChild(body);
      if (entry.warnings?.length) {
        const warning=document.createElement('p');
        warning.className='muted';
        warning.textContent=entry.warnings.join(' · ');
        card.appendChild(warning);
      }
      container.appendChild(card);
    }
    for (const ranking of report.rankings || []) {
      const best=ranking.hunts?.[0];
      if (!best) continue;
      const card=document.createElement('article');
      card.className='world-sample';
      const heading=document.createElement('strong');
      heading.textContent='Melhor hunt medida · '+ranking.account_id+' · '+ranking.pokemon_id;
      card.appendChild(heading);
      const summary=document.createElement('p');
      summary.textContent=best.hunt_id+' · objetivo: '+ranking.priority+
        ' · pontuação relativa: '+best.score.toLocaleString('pt-BR')+
        '. Recomendação offline, sem comando para o jogo.';
      card.appendChild(summary);
      container.appendChild(card);
    }
  } catch (error) {
    status.textContent='Relatório manual não pôde ser carregado: '+error.message;
  }
}
loadWorldPokeGrid();
