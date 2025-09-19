export const ALL_COINS = ["BTC","ETH","BNB","SOL","XRP","ADA","DOGE","TON","AVAX","DOT"];

export const state = {
  buyThreshold: 1.0,
  sellThreshold: 1.5,
  activeCoins: {}, // { BTC: { lastBuy: number|null } }
  notifs: []       // {id,text,type,time}
};

// localStorage helpers
export const storage = {
  save: (key, data) => {
    try {
      localStorage.setItem(key, JSON.stringify(data));
    } catch (e) {
      console.warn('Failed to save to localStorage:', e);
    }
  },
  
  load: (key, defaultValue = null) => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
      console.warn('Failed to load from localStorage:', e);
      return defaultValue;
    }
  },
  
  remove: (key) => {
    try {
      localStorage.removeItem(key);
    } catch (e) {
      console.warn('Failed to remove from localStorage:', e);
    }
  }
};

export const $  = (q, el=document) => el.querySelector(q);
export const $$ = (q, el=document) => Array.from(el.querySelectorAll(q));
export const toNum = v => Number(v ?? 0);
const pad = n => String(n).padStart(2, "0");
export const nowTime = () => { const d=new Date(); return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`; };

