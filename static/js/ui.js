import { $, $$, state, ALL_COINS, toNum, nowTime } from './state.js';
import { Api } from './api.js';

export function initThemeToggle(){
  const themeToggle = $('#theme-toggle');
  const themeIcon   = $('#theme-icon');
  const themeLabel  = $('#theme-label');
  const applyLabel = () => {
    const isDark = document.documentElement.classList.contains('dark');
    themeIcon.textContent = isDark ? '☀️' : '🌙';
    themeLabel.textContent = isDark ? 'لایت' : 'دارک';
    themeToggle?.setAttribute('aria-pressed', String(isDark));
  };
  themeToggle?.addEventListener('click', () => {
    const root = document.documentElement;
    const isDark = root.classList.toggle('dark');
    try { localStorage.setItem('theme', isDark ? 'dark' : 'light'); } catch(e){}
    applyLabel();
  });
  applyLabel();
}

export function initNotifications(){
  const notifBtn    = $('#notif-btn');
  const notifPanel  = $('#notif-panel');
  const notifList   = $('#notif-list');
  const notifBadge  = $('#notif-badge');
  const notifClear  = $('#notif-clear');
  const soundToggle = $('#sound-toggle');

  function renderList(){
    notifList.innerHTML = '';
    if(state.notifs.length===0){
      const li = document.createElement('li');
      li.className = 'px-3 py-2 text-gray-500 dark:text-gray-400';
      li.textContent = 'هیچ اعلانی ندارید.';
      notifList.appendChild(li);
    } else {
      state.notifs.slice().reverse().forEach(n=>{
        const li = document.createElement('li');
        li.className = 'px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-900/50';
        li.innerHTML = `
          <div class="flex items-start justify-between gap-2">
            <div class="flex-1">
              <div class="text-sm ${n.type==='buy'?'text-green-600 dark:text-green-400':'text-red-600 dark:text-red-400'} font-medium">${n.text}</div>
              <div class="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">${n.time}</div>
            </div>
            <button class="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" data-del="${n.id}" aria-label="حذف اعلان">حذف</button>
          </div>`;
        notifList.appendChild(li);
      });
      $$('[data-del]', notifList).forEach(btn=>{
        btn.addEventListener('click', ()=>{
          const id = btn.getAttribute('data-del');
          state.notifs = state.notifs.filter(x=>x.id!==id);
          updateBadge(); renderList();
        });
      });
    }
  }
  function updateBadge(){
    const c = state.notifs.length;
    if(c>0){
      notifBadge.textContent = c;
      notifBadge.classList.remove('hidden');
      notifBtn.classList.add('animate-pulse');
      setTimeout(()=>notifBtn.classList.remove('animate-pulse'), 800);
    } else notifBadge.classList.add('hidden');
  }
  function openPanel(){
    notifPanel.classList.remove('hidden');
    notifBtn.setAttribute('aria-expanded','true');
    const bd = document.createElement('div');
    bd.className='backdrop'; bd.id='notif-backdrop';
    document.body.appendChild(bd);
    bd.addEventListener('click', closePanel);
  }
  function closePanel(){
    notifPanel.classList.add('hidden');
    notifBtn.setAttribute('aria-expanded','false');
    document.getElementById('notif-backdrop')?.remove();
  }
  notifBtn?.addEventListener('click', ()=> notifPanel.classList.contains('hidden')? openPanel(): closePanel());
  notifClear?.addEventListener('click', ()=>{ state.notifs=[]; updateBadge(); renderList(); });
  document.addEventListener('keydown', (e)=>{ if(e.key==='Escape') closePanel(); });

  // expose helpers
  function addNotification({text,type}){
    const item={ id: Math.random().toString(36).slice(2), text, type, time: nowTime() };
    state.notifs.push(item); updateBadge(); renderList();
    if(soundToggle?.checked){ const a = document.getElementById('alert-sound'); a && a.play().catch(()=>{}); }
  }
  renderList(); updateBadge();
  return { addNotification, soundToggle };
}

export function initCoinsUI(addCoinCb, removeCoinCb, persistCb){
  const coinListEl = $('#coin-list');
  const coinSearchEl = $('#coin-search');
  const selectAllEl = $('#select-all');

  function renderCheckboxes(filter=''){
    coinListEl.innerHTML='';
    const f = filter.trim().toUpperCase();
    ALL_COINS.filter(s=>!f || s.includes(f)).forEach(sym=>{
      const li = document.createElement('li');
      li.innerHTML = `
        <label class="flex items-center gap-2 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-900/40 cursor-pointer">
          <input type="checkbox" class="coin-checkbox w-4 h-4" value="${sym}" />
          <span>${sym}/USDT</span>
        </label>`;
      coinListEl.appendChild(li);
    });
    $$('.coin-checkbox').forEach(cb=>{
      cb.checked = !!state.activeCoins[cb.value];
      cb.addEventListener('change', (e)=>{
        const sym = e.target.value;
        if(e.target.checked) addCoinCb(sym); else removeCoinCb(sym);
        updateSelectAllState(); persistCb();
      });
    });
    updateSelectAllState();
  }
  function updateSelectAllState(){
    const boxes = $$('.coin-checkbox');
    if(boxes.length===0){ selectAllEl.indeterminate=false; selectAllEl.checked=false; return; }
    const checked = boxes.filter(cb=>cb.checked).length;
    selectAllEl.checked = checked===boxes.length;
    selectAllEl.indeterminate = checked>0 && checked<boxes.length;
  }
  let t; coinSearchEl?.addEventListener('input', (e)=>{ clearTimeout(t); t=setTimeout(()=>renderCheckboxes(e.target.value),150); });
  selectAllEl?.addEventListener('change', (e)=>{
    const target = e.target.checked;
    $$('.coin-checkbox').forEach(cb=>{
      if(cb.checked!==target){ cb.checked=target; cb.dispatchEvent(new Event('change')); }
    });
    updateSelectAllState();
  });

  renderCheckboxes();
}

export function createCoinCard(symbol, refreshHandlers){
  const container = document.getElementById('coins-container');
  const card = document.createElement('section');
  card.className = 'card bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-4';
  card.id = 'card-'+symbol;
  card.innerHTML = `
    <div class="flex items-center justify-between gap-2">
      <h3 class="text-base font-semibold">${symbol}/USDT</h3>
      <div class="flex items-center gap-2">
        <a href="/signals/${symbol}/csv" class="text-xs bg-gray-100 dark:bg-gray-900/50 hover:bg-gray-200 dark:hover:bg-gray-900 px-2.5 py-1 rounded border border-gray-200 dark:border-gray-700">CSV</a>
        <button data-refresh="${symbol}" class="text-xs bg-blue-600 dark:bg-blue-700 text-white hover:bg-blue-700 dark:hover:bg-blue-800 px-2.5 py-1 rounded">بروزرسانی</button>
        <button data-remove="${symbol}" class="text-xs text-red-600 hover:text-red-700">حذف</button>
      </div>
    </div>
    <div class="mt-2 grid grid-cols-3 gap-2 text-center">
      <div class="col-span-3 sm:col-span-1">
        <div class="text-xs text-gray-500 dark:text-gray-400">قیمت لحظه‌ای</div>
        <div id="price-${symbol}" class="text-2xl font-bold text-green-600">--</div>
      </div>
      <div class="col-span-3 sm:col-span-1">
        <div class="text-xs text-gray-500 dark:text-gray-400">آخرین سیگنال</div>
        <div id="signal-${symbol}" class="font-medium">—</div>
      </div>
      <div class="col-span-3 sm:col-span-1">
        <div class="text-xs text-gray-500 dark:text-gray-400">سود تجمعی</div>
        <div id="profit-${symbol}" class="font-bold text-blue-600">0 $</div>
      </div>
    </div>
    <ul id="history-${symbol}" class="text-sm space-y-1 mt-3 text-right max-h-40 overflow-auto border border-gray-200 dark:border-gray-700 rounded-lg p-2 bg-gray-50 dark:bg-gray-900/40"></ul>
    <div class="mt-3 border border-gray-200 dark:border-gray-700 rounded-lg p-2 bg-white dark:bg-gray-800">
      <div class="flex items-center justify-between">
        <div class="text-xs text-gray-500 dark:text-gray-400">تحلیل چندبازه‌ای</div>
        <div id="conf-${symbol}" class="text-xs font-medium text-gray-700 dark:text-gray-300">اعتماد: --%</div>
      </div>
      <div id="tfa-${symbol}" class="mt-1 grid grid-cols-3 gap-1 text-[12px] text-center"></div>
    </div>
  `;
  container.appendChild(card);

  card.querySelector(`[data-remove="${symbol}"]`)?.addEventListener('click', refreshHandlers.onRemove);
  card.querySelector(`[data-refresh="${symbol}"]`)?.addEventListener('click', ()=>{
    refreshHandlers.onRefreshPrice(); refreshHandlers.onRefreshAnalysis();
  });
}

export const UIHelpers = {
  setProfit(symbol, totalProfit){
    const el = document.getElementById('profit-'+symbol);
    if(!el) return;
    el.textContent = Number(totalProfit).toFixed(2) + ' $';
    el.className = 'font-bold text-center ' + (totalProfit>=0 ? 'text-green-600':'text-red-600');
  },
  setLastSignal(symbol, txt){ const el = document.getElementById('signal-'+symbol); el && (el.textContent = txt); },
  pushHistory(symbol, lines){
    const box = document.getElementById('history-'+symbol);
    if(!box) return; box.innerHTML='';
    lines.forEach(t=>{ const li=document.createElement('li'); li.textContent=t; box.appendChild(li); });
  },
  setPrice(symbol, price){ const el=document.getElementById('price-'+symbol); el && (el.textContent = price.toFixed(2)+' $'); },
  setTFA(symbol, data){
    const box = document.getElementById('tfa-'+symbol);
    const conf = document.getElementById('conf-'+symbol);
    if(!box || !conf) return;
    const order=['5m','15m','1h'];
    const tf = data.timeframes || {};
    box.innerHTML='';
    order.forEach(iv=>{
      const it = tf[iv] || {};
      let tag='—';
      if(it.signal==='buy') tag='خرید'; else if(it.signal==='sell') tag='فروش'; else if(it.signal==='neutral') tag='خنثی';
      const c = it.close!=null ? Number(it.close).toFixed(2) : '--';
      const r = it.rsi14!=null ? Number(it.rsi14).toFixed(0) : '--';
      const pill = it.signal==='buy' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                 : it.signal==='sell'? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                 : 'bg-gray-100 text-gray-700 dark:bg-gray-900/40 dark:text-gray-300';
      const div=document.createElement('div');
      div.className=`rounded ${pill} px-2 py-1`;
      div.innerHTML = `<div class="font-medium">${iv}</div><div>${tag}</div><div class="opacity-80">C:${c} • RSI:${r}</div>`;
      box.appendChild(div);
    });
    conf.textContent = `اعتماد: ${Number(data.confidence||0)}%`;
  }
};
