export const ALL_COINS = ["BTC","ETH","BNB","SOL","XRP","ADA","DOGE","TON","AVAX","DOT"];

export const state = {
  buyThreshold: 1.0,
  sellThreshold: 1.5,
  activeCoins: {}, // { BTC: { lastBuy: number|null } }
  notifs: []       // {id,text,type,time}
};

export const $  = (q, el=document) => el.querySelector(q);
export const $$ = (q, el=document) => Array.from(el.querySelectorAll(q));
export const toNum = v => Number(v ?? 0);
const pad = n => String(n).padStart(2, "0");
export const nowTime = () => { const d=new Date(); return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`; };

