export async function getJSON(url){
  const res = await fetch(url);
  if(!res.ok) throw new Error(res.statusText);
  return res.json();
}
export async function postJSON(url, body){
  const res = await fetch(url,{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body)
  });
  if(!res.ok) throw new Error(res.statusText);
  return res.json().catch(()=> ({}));
}

export const Api = {
  settings: () => getJSON('/settings'),
  saveSettings: (buy, sell) => postJSON('/settings', { buy_threshold: buy, sell_threshold: sell }),
  prefs: () => getJSON('/prefs'),
  savePrefs: (partial) => postJSON('/prefs', partial),
  price: (sym) => getJSON(`/price/${sym}`),
  signals: (sym) => getJSON(`/signals/${sym}`),
  saveSignal: (sym, type, price) => postJSON(`/signals/${sym}`, { type, price }),
  analysis: (sym) => getJSON(`/analysis/${sym}?intervals=5m,15m,1h&limit=200`)
};
