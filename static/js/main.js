import { $, state, ALL_COINS, toNum, storage } from './state.js';
import { Api } from './api.js';
import { initThemeToggle, initNotifications, initCoinsUI, createCoinCard, UIHelpers } from './ui.js';

initThemeToggle();
const { addNotification } = initNotifications();

function addCoin(symbol){
  if(state.activeCoins[symbol]) return;
  state.activeCoins[symbol] = { lastBuy: null };

  createCoinCard(symbol, {
    onRemove: ()=>{
      delete state.activeCoins[symbol];
      document.getElementById('card-'+symbol)?.remove();
      persistCoinSelection();
      saveState();
    },
    onRefreshPrice: ()=> updatePrice(symbol),
    onRefreshAnalysis: ()=> updateAnalysis(symbol),
  });

  loadSignals(symbol);
  updatePrice(symbol);
  updateAnalysis(symbol);
  saveState();
}
function removeCoin(symbol){
  delete state.activeCoins[symbol];
  document.getElementById('card-'+symbol)?.remove();
  saveState();
}
function persistCoinSelection(){
  const coins = Object.keys(state.activeCoins);
  Api.savePrefs({ selected_coins: coins }).catch(()=>{});
}

// Save state to localStorage
function saveState(){
  storage.save('p-plus-state', {
    buyThreshold: state.buyThreshold,
    sellThreshold: state.sellThreshold,
    activeCoins: state.activeCoins
  });
}

// Load state from localStorage
function loadState(){
  const saved = storage.load('p-plus-state', {});
  if(saved.buyThreshold) state.buyThreshold = saved.buyThreshold;
  if(saved.sellThreshold) state.sellThreshold = saved.sellThreshold;
  if(saved.activeCoins) state.activeCoins = saved.activeCoins;
}

// Update UI from loaded state
function updateUIFromState(){
  // به‌روزرسانی تنظیمات
  $('#buy-threshold').value = state.buyThreshold;
  $('#sell-threshold').value = state.sellThreshold;
  
  // ایجاد کارت‌های ارزهای فعال
  Object.keys(state.activeCoins).forEach(symbol => {
    if(!document.getElementById('card-'+symbol)) {
      createCoinCard(symbol, {
        onRemove: ()=>{
          delete state.activeCoins[symbol];
          document.getElementById('card-'+symbol)?.remove();
          persistCoinSelection();
          saveState();
        },
        onRefreshPrice: ()=> updatePrice(symbol),
        onRefreshAnalysis: ()=> updateAnalysis(symbol),
      });
    }
  });
  
  // به‌روزرسانی چک‌باکس‌ها
  Object.keys(state.activeCoins).forEach(symbol => {
    const cb = document.querySelector(`.coin-checkbox[value="${symbol}"]`);
    if(cb) cb.checked = true;
  });
}

// Clear all state (for debugging)
function clearState(){
  state.activeCoins = {};
  state.buyThreshold = 1.0;
  state.sellThreshold = 1.5;
  storage.remove('p-plus-state');
  
  // پاک کردن UI
  document.querySelectorAll('.coin-card').forEach(card => card.remove());
  document.querySelectorAll('.coin-checkbox').forEach(cb => cb.checked = false);
  
  addNotification({ text: '🗑️ تمام اطلاعات پاک شد', type: 'info' });
}

// اضافه کردن توابع به window برای دسترسی از کنسول
window.clearState = clearState;
window.getState = () => state;
window.saveState = saveState;
window.loadState = loadState;

initCoinsUI(addCoin, removeCoin, persistCoinSelection);

// ---------- Settings ----------
async function loadSettings(){
  try{
    const data = await Api.settings();
    state.buyThreshold  = Number(data.first_buy_threshold ?? state.buyThreshold);
    state.sellThreshold = Number(data.sell_threshold ?? state.sellThreshold);
  }catch{}
  $('#buy-threshold').value  = state.buyThreshold;
  $('#sell-threshold').value = state.sellThreshold;
  saveState();
}
document.getElementById('settings-form')?.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const buy  = toNum($('#buy-threshold').value || state.buyThreshold);
  const sell = toNum($('#sell-threshold').value || state.sellThreshold);
  try{
    await Api.saveSettings(buy, sell);
    state.buyThreshold=buy; state.sellThreshold=sell;
    saveState();
    addNotification({ text: '✅ تنظیمات ذخیره شد', type: 'info' });
  }catch{
    addNotification({ text: '❌ خطا در ذخیره تنظیمات', type: 'info' });
  }
});

// ---------- Prefs (coins + sound) ----------
async function loadPrefs(){
  // ابتدا state را از localStorage بارگذاری کن
  loadState();
  
  try{
    const data = await Api.prefs();
    document.getElementById('sound-toggle').checked = !!data.notif_sound;
    // ساخت چک‌باکس‌ها قبلاً انجام شده؛ فقط تیک‌ها را اعمال می‌کنیم:
    const saved = Array.isArray(data.selected_coins) ? data.selected_coins : ['BTC','ETH','BNB'];
    saved.forEach(sym=>{
      const already = state.activeCoins[sym];
      if(!already) addCoin(sym);
      const cb = document.querySelector(`.coin-checkbox[value="${sym}"]`);
      if(cb && !cb.checked){ cb.checked=true; }
    });
  }catch{}
  
  // UI را با state بارگذاری شده به‌روزرسانی کن
  updateUIFromState();
}
document.getElementById('sound-toggle')?.addEventListener('change', (e)=>{
  Api.savePrefs({ notif_sound: !!e.target.checked }).catch(()=>{});
});

// دکمه پاک کردن state
document.getElementById('clear-state')?.addEventListener('click', (e)=>{
  e.preventDefault();
  if(confirm('آیا مطمئن هستید که می‌خواهید تمام اطلاعات را پاک کنید؟')) {
    clearState();
  }
});

// ---------- Signals / Price / Analysis ----------
async function loadSignals(symbol){
  try{
    const data = await Api.signals(symbol);
    const signals = data.signals || [];
    const totalProfit = data.total_profit || 0;
    if(state.activeCoins[symbol]) {
      state.activeCoins[symbol].lastBuy = (data.last_open_buy ?? null);
      saveState();
    }

    UIHelpers.setProfit(symbol, totalProfit);
    if(signals.length>0){
      const s0=signals[0];
      UIHelpers.setLastSignal(symbol, (s0.type==='buy'?'📈 خرید':'📉 فروش') + ' در ' + s0.price + ' $');
    } else UIHelpers.setLastSignal(symbol, '—');

    const lines = signals.map(sig=>{
      const emoji = sig.type==='buy'?'📈':'📉';
      const profitText = (sig.type==='sell' && sig.profit!==0) ? ` (سود/زیان: ${sig.profit} $)` : '';
      return `${emoji} ${sig.type==='buy'?'خرید':'فروش'} در ${sig.price} $ - ${sig.time}${profitText}`;
    });
    UIHelpers.pushHistory(symbol, lines);
  }catch(e){ console.error('signals error:', e); }
}

async function updatePrice(symbol){
  try{
    const data = await Api.price(symbol);
    const price = Number(data?.price);
    if(!price) return;
    UIHelpers.setPrice(symbol, price);
    checkSignal(symbol, price);
  }catch(e){ console.error('price error:', e); }
}

async function updateAnalysis(symbol){
  try{
    const data = await Api.analysis(symbol);
    UIHelpers.setTFA(symbol, data);
  }catch(e){}
}

// نمونه منطق سیگنال
function checkSignal(symbol, price){
  const st = state.activeCoins[symbol];
  if(!st) return;

  if(st.lastBuy===null && Math.random()<0.08){
    st.lastBuy = price;
    const msg = `📈 سیگنال خرید ${symbol} در ${price.toFixed(2)} $`;
    UIHelpers.setLastSignal(symbol, msg);
    addNotification({ text: msg, type: 'buy' });
    Api.saveSignal(symbol,'buy',price.toFixed(2)).then(()=>loadSignals(symbol)).catch(()=>{});
    saveState();
  }
  if(st.lastBuy!==null && price >= st.lastBuy * (1 + state.sellThreshold/100)){
    const msg = `📉 سیگنال فروش ${symbol} در ${price.toFixed(2)} $`;
    UIHelpers.setLastSignal(symbol, msg);
    st.lastBuy = null;
    addNotification({ text: msg, type: 'sell' });
    Api.saveSignal(symbol,'sell',price.toFixed(2)).then(()=>loadSignals(symbol)).catch(()=>{});
    saveState();
  }
}

// ---------- Loop ----------
let _tick=0;
setInterval(()=>{
  const syms = Object.keys(state.activeCoins);
  syms.forEach(updatePrice);
  _tick = (_tick+1)%3;
  if(_tick===0) syms.forEach(updateAnalysis);
}, 5000);

// ---------- Boot ----------
(async function boot(){
  await loadSettings();
  // ساخت چک‌باکس‌ها و UI در initCoinsUI انجام شده
  await loadPrefs();
})();
