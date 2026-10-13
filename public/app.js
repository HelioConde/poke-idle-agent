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
    const select = document.getElementById('finance-account-select');
    let path = '/api/finance';
    if (select?.value) {
      const selected = JSON.parse(select.value);
      path += '?' + new URLSearchParams(selected).toString();
    }
    const response = await fetch(path, {cache:'no-store'});
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const payload = await response.json();
    if (!payload.configured) {
      document.querySelectorAll('[data-finance]').forEach(el => { el.textContent = '—'; });
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

async function loadWorldCapture() {
  const status = document.getElementById('world-capture-banner');
  const container = document.getElementById('world-capture-results');
  if (!status || !container) return;
  container.replaceChildren();
  try {
    const response = await fetch('/api/world-capture', {cache:'no-store'});
    if (!response.ok) throw new Error('HTTP '+response.status);
    const payload = await response.json();
    if (!payload.configured) {
      status.textContent = 'Configure o assistente com --world-capture data/world_capture.json (somente arquivo manual).';
      return;
    }
    const report = payload.report;
    status.textContent = report.is_demo
      ? 'DADOS FICTÍCIOS — nenhuma conta real foi acessada; ações automáticas desativadas.'
      : 'PLANEJAMENTO MANUAL — escolha de Pokébola por conta, sem clicks nem scripts.';
    if (!report.accounts.length) {
      const empty=document.createElement('p');
      empty.textContent='Nenhuma conta cadastrada.';
      container.appendChild(empty);
      return;
    }
    for (const account of report.accounts) {
      const card=document.createElement('article');
      card.className='world-sample';
      const heading=document.createElement('strong');
      heading.textContent=account.profile_id+' · '+account.account_id+
        (account.vip_reported_manually?' · VIP informado':' · Gratuito');
      card.appendChild(heading);
      const detail=document.createElement('p');
      detail.textContent=account.reason;
      card.appendChild(detail);
      const stock=document.createElement('p');
      const available=Object.entries(account.stock||{})
        .map(([name,count])=>name+': '+Number(count).toLocaleString('pt-BR'));
      stock.textContent='Pokébolas anotadas: '+(available.length?available.join(' · '):'Sem estoque conhecido');
      card.appendChild(stock);
      const history=document.createElement('p');
      const h=account.history;
      history.textContent='Tentativas anotadas: '+h.attempts+
        ' · Capturas: '+h.captures+
        ' · Shinies: '+h.shiny_captures;
      card.appendChild(history);
      const mode=document.createElement('p');
      mode.className='muted';
      mode.textContent='Modo: '+account.allowed_method+' · Execução externa: DESATIVADA';
      card.appendChild(mode);
      container.appendChild(card);
    }
  } catch(error) {
    status.textContent='Não foi possível analisar as capturas manuais: '+error.message;
  }
}
loadWorldCapture();


async function loadRegisteredAccounts() {
  const status = document.getElementById('accounts-status');
  const grid = document.getElementById('accounts-grid');
  const select = document.getElementById('finance-account-select');
  if (!status || !grid || !select) return;
  try {
    const response = await fetch('/api/accounts', {cache:'no-store'});
    if (!response.ok) throw Error('HTTP ' + response.status);
    const payload = await response.json();
    grid.replaceChildren();
    select.replaceChildren();
    const initial = document.createElement('option');
    initial.value = '';
    initial.textContent = 'Selecione uma conta IO para consultar o livro-caixa';
    select.appendChild(initial);
    status.textContent = payload.configured
      ? payload.accounts.length + ' conta(s) cadastrada(s) localmente.'
      : 'Nenhuma conta cadastrada. Use INICIAR-TUDO.bat --setup para cadastrar.';
    for (const entry of payload.accounts) {
      const card=document.createElement('article');
      card.className='world-sample';
      const name=document.createElement('strong');
      name.textContent=entry.game.toUpperCase()+' · '+entry.profile_id+' / '+entry.account_id;
      card.appendChild(name);
      const info=document.createElement('p');
      info.textContent='Treinador: '+(entry.trainer_level ?? 'desconhecido')+
         ' · Equipe: '+entry.pokemon_count+
         ' · Ativo: '+(entry.active_pokemon || 'não selecionado');
      card.appendChild(info);
      grid.appendChild(card);
      if(entry.game==='io'){
        const opt=document.createElement('option');
        opt.value=JSON.stringify({game:entry.game,profile:entry.profile_id,account:entry.account_id});
        opt.textContent=entry.profile_id+' / '+entry.account_id;
        select.appendChild(opt);
      }
    }
    select.addEventListener('change', loadFinance);
    await loadFinance();
  } catch (error) {
    status.textContent='Não foi possível carregar o cadastro: '+error.message;
  }
}

// Este painel não usa números de demonstração como telemetria nem agrega
// XP/h de abas diferentes ou mistura World com IO.
function updateLiveIoSummary(payload){
  const set=(id,value)=>{const node=document.getElementById(id);if(node)node.textContent=value;};
  const all=(payload?.tabs||[]).filter(item=>item.game==='io');
  const current=all.filter(item=>{
    const observation=item.observation||{},stats=item.telemetry?.stats||{};
    return item.route==='app' && observation.xp_trainer_scoped===true &&
      observation.telemetry_protocol===2 &&
      observation.reader_version==='trainer-xp-scoped-v1' &&
      observation.content_state==='responded' &&
      Number.isInteger(stats.level) && stats.level>0 &&
      typeof stats.xp_current==='number' && Number.isFinite(stats.xp_current) &&
      stats.xp_current>=0;
  }).sort((a,b)=>(a.age_seconds??1e9)-(b.age_seconds??1e9));
  const chosen=current[0];
  if(!chosen || !(chosen.age_seconds<=90)){
    set('live-state',!all.length
      ? 'Sem abas IO sincronizadas · conecte a extensão e abra o jogo.'
      : 'Abas encontradas, mas sem leitura recente e validada do XP do treinador.');
    set('live-trainer-level','—');
    set('live-trainer-xp','—');
    set('live-trainer-rate','—');
    set('live-trend','Aguardando');
    set('live-note','Nenhum número de exemplo é usado neste resumo. A telemetria precisa ser recente e confirmada.');
    return;
  }
  const stats=chosen.telemetry.stats;
  const fmt=value=>value.toLocaleString('pt-BR',{maximumFractionDigits:1});
  const max=typeof stats.xp_max==='number' && Number.isFinite(stats.xp_max)
    ? ' / '+stats.xp_max.toLocaleString('pt-BR') : '';
  set('live-state','Leitura real do treinador confirmada · '+all.length+
    ' aba(s) IO · perfil Chrome '+(chosen.profile_label||'sem rótulo')+
    ' · atualização há '+chosen.age_seconds+'s.');
  set('live-trainer-level',String(stats.level));
  set('live-trainer-xp',stats.xp_current.toLocaleString('pt-BR')+max);
  const rate=chosen.xp_per_hour;
  set('live-trainer-rate',typeof rate==='number' && Number.isFinite(rate)
    ?fmt(rate)+' XP/h':'Aguardando amostras');
  const windows=chosen.xp_windows||{};
  const mature=['5m','15m','60m'].filter(key=>
    typeof windows[key]==='number' && Number.isFinite(windows[key]) && windows[key]>=0);
  set('live-trend',mature.length?mature.map(key=>key+': '+fmt(windows[key])).join(' · '):'Aguardando');
  const warning=all.length>1
    ?' Há mais de uma aba IO: este resumo exibe só a leitura mais recente, sem somar XP.'
    :'';
  set('live-note','XP/h recente é calculado entre leituras e pode variar muito. '+
    'As médias de 5/15/60 min só aparecem quando a janela estiver madura. '+
    'Perfil Chrome não comprova identidade de conta ou hunt.'+warning);
}

async function refreshUnifiedTabs() {
  const status = document.getElementById('unified-status');
  const grid = document.getElementById('tabs-grid');
  if(!status || !grid) return;
  try {
    const res=await fetch('/api/tabs',{cache:'no-store'});
    if(!res.ok) throw Error('HTTP '+res.status);
    const payload=await res.json();
    updateLiveIoSummary(payload);
    status.textContent='Monitor IO ativo · '+payload.tabs.length+' aba(s) · '+
      payload.profiles+' perfil(is) Chrome';
    grid.replaceChildren();
    if(!payload.tabs.length){
      const empty=document.createElement('p');
      empty.className='muted';
      empty.textContent='Nenhuma aba sincronizada. Abra o Chrome com a extensão local emparelhada.';
      grid.appendChild(empty); return;
    }
    for(const item of payload.tabs.slice(0,40)){
      const card=document.createElement('article');
      card.className='world-sample';
      const heading=document.createElement('strong');
      heading.textContent=item.game.toUpperCase()+' · '+item.profile_label+' · '+
        (item.active?'aba visível':'aba inativa');
      card.appendChild(heading);
      const paragraph=document.createElement('p');
      if(item.game === 'io'){
        const stats = item.telemetry?.stats || {};
        const legacy=item.observation?.status==='legacy_protocol';
        const xp=legacy ? 'XP/h bloqueado: leitor desatualizado'
          : ((typeof item.xp_per_hour==='number')
            ? item.xp_per_hour.toLocaleString('pt-BR',{maximumFractionDigits:1})+' XP/h'
            : 'XP/h: aguardando segunda amostra');
        const trainerXp=(typeof stats.xp_current==='number' && typeof stats.xp_max==='number')
          ? stats.xp_current.toLocaleString('pt-BR')+' / '+stats.xp_max.toLocaleString('pt-BR')
          : 'não confirmado';
        const source=item.observation?.xp_trainer_scoped===true
          ? 'origem: treinador confirmada'
          : 'origem do XP: não confirmada';
        const movingRates=Object.entries(item.xp_windows||{})
          .filter(([period,value])=>['5m','15m','60m'].includes(period)
            && typeof value==='number' && Number.isFinite(value) && value>=0)
          .map(([period,value])=>period+': '+
            value.toLocaleString('pt-BR',{maximumFractionDigits:1})+' XP/h');
        const rateTrend=movingRates.length
          ? ' · médias observadas: '+movingRates.join(' · ')
          : ' · médias de 5/15/60 min: aguardando janela suficiente';
        const reader=legacy
          ? 'leitor desatualizado; recarregue extensão e /app'
          : (item.observation?.content_state==='outdated'
            ? 'content script desatualizado'
            : 'leitor: '+(item.observation?.content_state || 'sem confirmação'));
        paragraph.textContent=xp+' · Nível: '+(stats.level ?? 'desconhecido')+
          ' · XP treinador: '+trainerXp+' · '+source+
          ' · '+(item.observation?.xp_ambiguous
            ? 'XP ambíguo: '+item.observation.xp_candidates+' barras distintas, sem XP/h'
            : (item.advice?.reason || 'Leitura IO pendente'))+
          ' · '+reader+rateTrend+
          ' · Atualizada há '+item.age_seconds+'s';
      } else {
        paragraph.textContent='Poke Idle World: somente identificação da aba; telemetria privada desativada.';
      }
      card.appendChild(paragraph);
      grid.appendChild(card);
    }
    const auditStatus=document.getElementById('io-automation-status');
    const auditGrid=document.getElementById('io-automation-grid');
    if(auditStatus && auditGrid){
      // Preservar a expansão escolhida pelo usuário entre polls de 5 segundos.
      const openAudits=new Set([...auditGrid.querySelectorAll('details.audit-details[open]')]
        .map(detail=>detail.dataset.auditKey).filter(Boolean));
      auditGrid.replaceChildren();
      const ioTabs=payload.tabs.filter(item=>item.game==='io' && item.io_audit);
      if(!ioTabs.length){
        const readerReady=payload.tabs.some(item=>item.game==='io' &&
          item.route==='app' && item.observation?.content_state==='responded');
        auditStatus.textContent=readerReady
          ? 'XP do treinador recebido, mas auditoria IO ausente. Confirme a versão da extensão no Chrome, recarregue-a e, quando for seguro para o farm, atualize a aba do jogo; depois sincronize novamente.'
          : 'Aguardando auditoria IO da extensão ou resposta atualizada da aba do jogo.';
      }else{
        auditStatus.textContent=ioTabs.length+' aba(s) IO observada(s). Leitura apenas: nenhum controle está autorizado para execução.';
        const mapStatus={open:'Mapa aberto',closed:'Mapa fechado',
                         unknown:'Mapa ainda não identificado'};
        const controlLabels={
          trainer_panel:'Treinador',active_pokemon_panel:'Pokémon ativo',
          inventory:'Inventário',surrender:'Desistir — proibido',
          hunt_map:'Botão Mapa',map_dialog:'Janela Mapa',
          native_capture_until:'Captura até conseguir',
          native_capture_repeat:'Lançamento contínuo',
          native_revive:'Revive nativo',native_potion:'Poções nativas',
          native_return_hunt:'Voltar à hunt (nativo)'
        };
        for(const io of ioTabs){
          const audit=io.io_audit;
          const section=document.createElement('article');
          section.className='world-sample';
          const heading=document.createElement('strong');
          heading.textContent=(io.profile_label||'Perfil Chrome')+
            ' · aba '+String(io.tab_id)+' · '+(mapStatus[audit.map_state]||'Mapa não verificado');
          const summary=document.createElement('p');
          const sceneLabels={
            hunt_scene:'cena de hunt exibida',
            center_scene:'cena de Centro Pokémon exibida',
            conflict:'sinais de cena conflitantes',
            unknown:'cena não identificada'
          };
          summary.textContent='Telemetria há '+String(io.age_seconds)+'s · '+
            (audit.farm_state==='active'
              ? 'texto do painel sugere atividade'
              : 'estado do farm não confirmado')+
            ' · '+(sceneLabels[audit.scene_indicator]||'cena ainda não auditada')+
            ' · nenhuma ação liberada. Cenas visuais não comprovam farm ativo no servidor.';
          const hint=audit.hunt_hint;
          if(hint && ['matching_displays','single_display','ambiguous','unavailable'].includes(hint.status)){
            const encounter=document.createElement('p');
            if(hint.status==='matching_displays' || hint.status==='single_display'){
              encounter.textContent='Encontro exibido no HUD: '+hint.label+
                ' · nível '+String(hint.level)+
                (hint.status==='matching_displays'?' · dois indicadores coincidem':' · apenas um indicador')+
                '. Pode ser um Pokémon selvagem; NÃO identifica a hunt ou o mapa.';
            }else{
              encounter.textContent=hint.status==='ambiguous'
                ? 'Encontro não confirmado: indicadores visuais divergentes.'
                : 'Encontro indisponível no HUD.';
            }
            section.appendChild(encounter);
          }
          const structure=audit.map_structure;
          if(structure && ['observed','body_missing','not_open'].includes(structure.status)){
            const mapInfo=document.createElement('p');
            if(structure.status==='observed'){
              if(Number.isInteger(structure.rendered_regions) &&
                 Number.isInteger(structure.rendered_markers)){
                mapInfo.textContent='Mapa aberto · regiões liberadas/renderizadas: '+
                  structure.available_regions+'/'+structure.rendered_regions+
                  ' · marcadores desbloqueados/renderizados: '+
                  structure.unlocked_markers+'/'+structure.rendered_markers+
                  ' · marcadores destacados: '+structure.highlighted_markers+
                  '. Contagens do mapa filtrado: não comprovam hunt atual ou acesso real.';
              }else{
                mapInfo.textContent='Estrutura do Mapa (versão anterior): '+
                  structure.buttons+' botões · '+structure.links+' links · '+
                  structure.candidate_markers+' atributos candidatos.';
              }
            }else if(audit.map_state==='open'){
              mapInfo.textContent='Mapa aberto, mas o corpo do modal não foi localizado.';
            }else{
              mapInfo.textContent='Mapa fechado: marcadores ocultos não são contados como hunts disponíveis.';
            }
            section.appendChild(mapInfo);
          }
          const details=document.createElement('details');
          details.className='audit-details';
          details.dataset.auditKey=String(io.profile_id||io.profile_label||'chrome')+
            ':'+String(io.window_id)+':'+String(io.tab_id);
          details.open=openAudits.has(details.dataset.auditKey);
          const detailsSummary=document.createElement('summary');
          detailsSummary.textContent='Ver controles auditados ('+
            Object.keys(audit.controls||{}).length+') · somente leitura · Desistir bloqueado';
          const controls=document.createElement('div');
          controls.className='world-results audit-control-list';
          for(const [name,control] of Object.entries(audit.controls||{})){
            const card=document.createElement('article');card.className='world-sample';
            const label=document.createElement('strong');
            label.textContent=controlLabels[name]||name.replaceAll('_',' ');
            const detail=document.createElement('p');
            if(control.policy==='permanently_blocked'){
              detail.textContent='BLOQUEADO: risco de derrota/perda de XP.';
            }else{
              const toggle={on:'ativado no jogo',off:'desativado no jogo',
                            unknown:'estado não confirmado'};
              detail.textContent=(control.present?'Detectado':'Não detectado')+
                ' · apenas leitura'+(control.toggle_state
                ? ' · '+(toggle[control.toggle_state]||'estado não confirmado'):'');
            }
            card.append(label,detail);
            controls.appendChild(card);
          }
          details.append(detailsSummary,controls);
          section.append(heading,summary,details);
          const recommendations=Array.isArray(io.advisory_queue)
            ? io.advisory_queue.slice(0,3) : [];
          if(recommendations.length){
            const adviceTitle=document.createElement('strong');
            adviceTitle.textContent='Recomendações para revisar (sem execução)';
            const adviceList=document.createElement('ul');
            for(const rec of recommendations){
              if(rec.status!=='review_only'||rec.action_authorized!==false)continue;
              const adviceItem=document.createElement('li');
              adviceItem.textContent=(rec.priority==='high'?'Atenção: ':'')+rec.message;
              adviceList.appendChild(adviceItem);
            }
            section.append(adviceTitle,adviceList);
          }
          auditGrid.appendChild(section);
        }
      }
    }
  }catch(error){
    updateLiveIoSummary({tabs:[]});
    const live=document.getElementById('live-state');
    if(live)live.textContent='Não foi possível consultar o monitor local: '+error.message;
    status.textContent='Monitor não iniciado: '+error.message;
    grid.replaceChildren();
  }
}

async function loadIoHuntComparison(){
  const status=document.getElementById('io-hunt-status');
  const grid=document.getElementById('io-hunt-results');
  const objective=document.getElementById('io-hunt-objective');
  if(!status||!grid||!objective)return;
  grid.replaceChildren();
  const goal=['xp','resources','balanced'].includes(objective.value)
    ? objective.value : 'xp';
  try{
    const response=await fetch('/api/io/hunts?objective='+encodeURIComponent(goal),
      {cache:'no-store'});
    if(!response.ok)throw Error('HTTP '+response.status);
    const report=await response.json();
    if(!report.configured){
      status.textContent=report.reason||'Medições manuais IO ainda não configuradas.';
      return;
    }
    status.textContent='Comparação offline por conta cadastrada e Pokémon ativo. '+
      'Nenhuma hunt atual foi confirmada automaticamente; nenhuma ação será executada.';
    for(const row of report.comparisons||[]){
      const card=document.createElement('article');
      card.className='world-sample';
      const title=document.createElement('strong');
      title.textContent=row.profile_id+' · '+row.account_id+
        ' · Pokémon: '+(row.pokemon_id||'não identificado');
      card.appendChild(title);
      if(row.ranking?.status!=='ranked'){
        const need=document.createElement('p');
        need.textContent=row.ranking?.reason||'Ainda sem medições suficientes.';
        card.appendChild(need);
      }else{
        const caption=document.createElement('p');
        caption.textContent='Ranking com medições fornecidas manualmente, não vinculado à aba Chrome.';
        card.appendChild(caption);
        const ranking=document.createElement('ol');
        for(const hunt of row.ranking.ranked.slice(0,8)){
          const item=document.createElement('li');
          const xp=Number.isFinite(hunt.xp_per_hour)
            ? hunt.xp_per_hour.toLocaleString('pt-BR',{maximumFractionDigits:1})
            : 'não medido';
          item.textContent=hunt.hunt+' · '+xp+' XP/h · '+
            hunt.minutes+' min · derrotas/h: '+hunt.defeats_per_hour;
          ranking.appendChild(item);
        }
        card.appendChild(ranking);
      }
      grid.appendChild(card);
    }
    if(!(report.comparisons||[]).length)status.textContent='Nenhuma conta IO cadastrada para comparação.';
  }catch(error){
    status.textContent='Comparador indisponível: '+String(error.message||error);
  }
}

async function loadWorldIVs() {
  const status=document.getElementById('world-ivs-banner');
  const grid=document.getElementById('world-ivs-results');
  if(!status || !grid) return;
  grid.replaceChildren();
  try {
    const res=await fetch('/api/world-ivs',{cache:'no-store'});
    if(!res.ok) throw Error('HTTP '+res.status);
    const payload=await res.json();
    if(!payload.configured){
      status.textContent=payload.reason;
      return;
    }
    status.textContent=payload.report.source==='demo'
      ? 'DADOS FICTÍCIOS — calculados localmente, não conferidos no jogo.'
      : 'DADOS MANUAIS — projeções matemáticas, não resultados comprovados.';
    for(const p of payload.report.pokemon.slice(0,40)){
      const card=document.createElement('article');
      card.className='world-sample';
      const heading=document.createElement('strong');
      heading.textContent=p.name+' · nível atual '+p.current_level;
      card.appendChild(heading);
      const details=document.createElement('p');
      details.textContent=p.projections.map(v=>
        'Nível '+v.level+': poder projetado '+(v.power ?? 'desconhecido')).join(' · ');
      card.appendChild(details);
      grid.appendChild(card);
    }
  }catch(error){status.textContent='Não foi possível calcular IVs: '+error.message;}
}
const ioObjective=document.getElementById('io-hunt-objective');
if(ioObjective)ioObjective.addEventListener('change',loadIoHuntComparison);
loadIoHuntComparison();
loadRegisteredAccounts();
refreshUnifiedTabs();
setInterval(refreshUnifiedTabs, 5000);
loadWorldIVs();
