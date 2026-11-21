/* 四级词库 —— 单页应用
 * 数据源：words.md（唯一真源）
 * 进度：localStorage
 */
(() => {
"use strict";

// ---------------------------------------------------------------------------
// 工具
// ---------------------------------------------------------------------------
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[c]));
const escapeReg = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const dateStr = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const todayStr = () => dateStr(new Date());
const addDays = (s, n) => { const d = new Date(s + "T00:00:00"); d.setDate(d.getDate() + n); return dateStr(d); };
const daysUntil = (s) => {
  const [y, m, d] = s.split("-").map(Number);
  const target = Date.UTC(y, m - 1, d);
  const now = new Date();
  const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((target - today) / 86400000);
};
const shuffle = (arr) => {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
};
const debounce = (fn, ms) => { let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); }; };
let toastTimer = null;
function toast(msg) {
  const el = $("#toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 1800);
}
function shortGloss(g, max = 40) {
  g = String(g || "").replace(/\s+/g, " ").trim();
  if (!g) return "";
  const parts = g.split(/[；;]/).map((s) => s.trim()).filter(Boolean);
  let out = "";
  for (const p of parts) {
    const next = out ? out + "；" + p : p;
    if (next.length > max) break;
    out = next;
  }
  if (!out) out = g.slice(0, max);
  if (out.length < g.length) out += "…";
  return out;
}
function greeting() {
  const h = new Date().getHours();
  if (h < 5) return "夜深了";
  if (h < 11) return "早上好";
  if (h < 14) return "中午好";
  if (h < 18) return "下午好";
  return "晚上好";
}

// ---------------------------------------------------------------------------
// 图标
// ---------------------------------------------------------------------------
const ICONS = {
  book: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5V5.5Z"/><path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H20"/>',
  link: '<path d="M9.5 14.5 14.5 9.5"/><path d="M7 17a4 4 0 0 1 0-5.7l2.3-2.3a4 4 0 0 1 5.7 0"/><path d="M17 7a4 4 0 0 1 0 5.7l-2.3 2.3a4 4 0 0 1-5.7 0"/>',
  cards: '<rect x="3" y="7" width="13" height="14" rx="2"/><path d="M8 3h11a2 2 0 0 1 2 2v12"/>',
  chart: '<path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-7"/><path d="M22 20H2"/>',
  speaker: '<path d="M11 5 6 9H3v6h3l5 4V5Z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/>',
  back: '<path d="M15 18l-6-6 6-6"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
  refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>',
  download: '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 21h16"/>',
  upload: '<path d="M12 21V9"/><path d="m7 14 5-5 5 5"/><path d="M4 3h16"/>',
  trash: '<path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 14h10l1-14"/>',
};
function icon(name, cls = "") {
  return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`;
}

// ---------------------------------------------------------------------------
// 词库解析
// ---------------------------------------------------------------------------
const POS_RE = /(?<![A-Za-z])(?:vt|vi|adj|adv|prep|pron|conj|num|art|det|phr|idm|aux|int|n|v)(?:\.?\/[a-z]+)?\./i;
const POS_SENSE_RE = /^((?:vt|vi|adj|adv|prep|pron|conj|num|art|det|phr|idm|aux|int|n|v)(?:\.?\/[a-z]+)?\.)\s*(.*)$/i;

function parseWords(md) {
  const words = [];
  const bad = [];
  let cur = null;
  for (const raw of md.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith("#") || line.startsWith(">") || line.startsWith("<!--") || line.startsWith("|")) continue;

    if (line.startsWith("- ")) {
      if (cur) {
        const t = line.slice(2).trim();
        const m = t.match(/^([^:：]{1,4})\s*[:：]\s*(.*)$/);
        if (m && /^(辨析|例|记|错|近义|相似|搭配|注意|变形|来源|备注|词根|联想|发音|用法)$/.test(m[1])) {
          cur.notes.push({ type: m[1] === "近义" || m[1] === "相似" ? m[1] : m[1], text: m[2] });
        } else {
          cur.notes.push({ type: "备注", text: t });
        }
      }
      continue;
    }

    const tags = { 族: [], 混: [], 近: [] };
    let body = line.replace(/\[(族|混|近):([^\]]*)\]/g, (_, k, v) => {
      tags[k] = v.split(/[,，、\s]+/).filter(Boolean);
      return " ";
    }).trim();

    let ipa = "";
    const im = body.match(/\/([^/\n]{1,40})\/\s*$/) || body.match(/\s\/([^/\n\u4e00-\u9fff]{1,40})\//);
    if (im) {
      ipa = "/" + im[1].trim() + "/";
      body = (body.slice(0, im.index) + " " + body.slice(im.index + im[0].length)).trim();
    }

    const pm = body.match(POS_RE);
    const cjk = body.search(/[\u4e00-\u9fff]/);
    const cut = pm && (cjk === -1 || pm.index < cjk) ? pm.index : cjk;
    if (cut <= 0) { bad.push(line); continue; }
    const word = body.slice(0, cut).trim().replace(/\s+/g, " ");
    if (!/^[A-Za-z][A-Za-z'’\- ]*$/.test(word)) { bad.push(line); continue; }
    const sensesRaw = body.slice(cut).trim().replace(/[;；]\s*(?=(?:vt|vi|adj|adv|prep|pron|conj|num|art|det|phr|idm|aux|int|n|v)\.)/gi, "｜");
    const senses = [];
    for (const part of sensesRaw.split(/[｜|]/)) {
      const s = part.trim();
      if (!s) continue;
      const m = s.match(POS_SENSE_RE);
      if (m) senses.push({ pos: m[1].replace(/\.$/, "").toLowerCase(), gloss: m[2].trim() });
      else senses.push({ pos: "", gloss: s });
    }
    if (!senses.length) { bad.push(line); continue; }
    cur = { word, key: word.toLowerCase(), senses, ipa, notes: [], tags, raw: line };
    words.push(cur);
  }
  return { words, bad };
}

function dedupeWords(list) {
  const map = new Map();
  const dupes = [];
  for (const w of list) {
    if (!map.has(w.key)) { map.set(w.key, w); continue; }
    dupes.push(w.key);
    const cur = map.get(w.key);
    for (const s of w.senses) {
      if (!cur.senses.some((x) => x.pos === s.pos && x.gloss === s.gloss)) cur.senses.push(s);
    }
    for (const n of w.notes) {
      if (!cur.notes.some((x) => x.type === n.type && x.text === n.text)) cur.notes.push(n);
    }
    for (const t of ["族", "混", "近"]) {
      for (const x of w.tags[t] || []) if (!cur.tags[t].includes(x)) cur.tags[t].push(x);
    }
    if (!cur.ipa && w.ipa) cur.ipa = w.ipa;
  }
  return { words: Array.from(map.values()), dupes };
}

// ---------------------------------------------------------------------------
// 全局状态
// ---------------------------------------------------------------------------
const state = {
  loaded: false,
  words: [],
  byKey: new Map(),
  badLines: [],
  dupes: [],
  missingRefs: [],
  families: [],
  familyByWord: new Map(),
  confusable: [],
  synonyms: [],
  confusableByWord: new Map(),
  synonymByWord: new Map(),
  similar: new Map(),
  suffix: new Map(),
  rhyme: new Map(),
  progress: null,
  session: null,
  summary: null,
  wordStack: [],
  wordCurrent: null,
  wordBack: false,
  relTab: "mix",
  list: { q: "", filter: "all", sort: "alpha", letter: "" },
};

// ---------------------------------------------------------------------------
// 进度 / SRS
// ---------------------------------------------------------------------------
const STORE = "cet4.progress.v1";
const INTERVALS = [0, 1, 2, 4, 7, 14];
const EXAM_DATE = "2026-12-12"; // 下次四级考试日期
const DEFAULT_REVIEW = 30;

function freshProgress() {
  return { v: 1, words: {}, days: {}, settings: { dailyReview: DEFAULT_REVIEW }, streak: { last: null, count: 0 } };
}
function migrateProgress(p) {
  if (!p || typeof p !== "object") return freshProgress();
  p.v = 1;
  p.words = p.words || {};
  p.days = p.days || {};
  const oldSettings = p.settings || {};
  p.settings = Object.assign({}, oldSettings);
  p.settings.dailyReview = Number(p.settings.dailyReview) || Number(oldSettings.dailyNew) || DEFAULT_REVIEW;
  delete p.settings.dailyNew;
  p.streak = p.streak || { last: null, count: 0 };
  return p;
}
function loadProgress() {
  try {
    const raw = localStorage.getItem(STORE);
    if (raw) return migrateProgress(JSON.parse(raw));
  } catch (e) { /* localStorage 不可用 */ }
  return freshProgress();
}
function saveProgress() {
  try { localStorage.setItem(STORE, JSON.stringify(state.progress)); } catch (e) { /* 忽略 */ }
}
function getP(word) { return state.progress.words[word] || null; }
function todayStats() {
  return state.progress.days[todayStr()] || { reviewed: 0, right: 0, new: 0, words: {} };
}
function dueWords() {
  const today = todayStr();
  return state.words.filter((w) => {
    const p = getP(w.word);
    return p && p.box > 0 && p.due && p.due <= today;
  });
}
function newWords() {
  return state.words.filter((w) => !getP(w.word));
}
function todayWordList() {
  const today = todayStr();
  const d = state.progress.days[today];
  if (d && d.words && Object.keys(d.words).length) {
    return Object.keys(d.words).map((w) => state.byKey.get(w)).filter(Boolean);
  }
  return state.words.filter((w) => getP(w.word)?.last === today);
}
function todayWordCount() { return todayWordList().length; }
function todayMasteredCount() {
  return todayWordList().filter((w) => (getP(w.word)?.box || 0) >= 4).length;
}
function todayMasteryRate() {
  const n = todayWordCount();
  return n ? Math.round((todayMasteredCount() / n) * 100) : 0;
}
function updateStreak(today) {
  const s = state.progress.streak;
  if (s.last === today) return;
  s.count = s.last === addDays(today, -1) ? (s.count || 0) + 1 : 1;
  s.last = today;
}
function gradeWord(word, ok) {
  const today = todayStr();
  const wasNew = !getP(word);
  const p = getP(word) || { box: 0, right: 0, wrong: 0, seen: 0 };
  p.seen = (p.seen || 0) + 1;
  if (ok) {
    p.right = (p.right || 0) + 1;
    p.box = Math.min(5, (p.box || 1) + 1);
  } else {
    p.wrong = (p.wrong || 0) + 1;
    p.box = 1;
  }
  p.last = today;
  p.due = addDays(today, INTERVALS[p.box]);
  state.progress.words[word] = p;

  const d = state.progress.days[today] || { reviewed: 0, right: 0, new: 0, words: {} };
  d.words = d.words || {};
  const wd = d.words[word] || { right: 0, wrong: 0 };
  if (ok) wd.right += 1; else wd.wrong += 1;
  d.words[word] = wd;
  d.reviewed += 1;
  if (ok) d.right += 1;
  if (wasNew) d.new += 1;
  state.progress.days[today] = d;
  updateStreak(today);
  saveProgress();
}
function markWord(word, level) {
  const today = todayStr();
  const p = getP(word) || { right: 0, wrong: 0, seen: 0 };
  if (level === "known") { p.box = 5; p.due = addDays(today, 14); }
  else if (level === "fuzzy") { p.box = 2; p.due = addDays(today, 1); }
  else { p.box = 1; p.due = addDays(today, 1); }
  p.last = today;
  p.seen = (p.seen || 0) + 1;
  state.progress.words[word] = p;
  saveProgress();
}
function reviewTarget() {
  return Math.max(1, Math.min(200, Math.round(Number(state.progress.settings.dailyReview) || DEFAULT_REVIEW)));
}
function dailyRemaining() {
  return Math.max(0, reviewTarget() - todayWordCount());
}
function getQueue() {
  const remain = dailyRemaining();
  if (remain <= 0) return [];
  const due = dueWords().sort((a, b) => {
    const pa = getP(a.word), pb = getP(b.word);
    return pa.due.localeCompare(pb.due) || (pa.box - pb.box) || a.word.localeCompare(b.word);
  });
  const picked = due.slice(0, remain);
  if (picked.length < remain) {
    picked.push(...shuffle(newWords()).slice(0, remain - picked.length));
  }
  return picked;
}
function mixWrongCount(word) {
  return state.session?.mixWrong?.get(word) || 0;
}
function mixBox(word) {
  return Math.max(1, 5 - mixWrongCount(word));
}
function finalizeMixWord(word) {
  const s = state.session;
  if (!s || s.mode !== "mix") return;
  const p = getP(word);
  if (!p) return;
  const box = mixBox(word);
  p.box = box;
  p.due = addDays(todayStr(), INTERVALS[box]);
  saveProgress();
}
function trackMixAnswer(word, ok) {
  const s = state.session;
  if (!s || s.mode !== "mix") return;
  if (!s.mixWrong) s.mixWrong = new Map();
  if (!ok) s.mixWrong.set(word, (s.mixWrong.get(word) || 0) + 1);
  if (s.queue.indexOf(word, s.index + 1) === -1) finalizeMixWord(word);
}

// ---------------------------------------------------------------------------
// 索引
// ---------------------------------------------------------------------------
function buildIndexes() {
  state.byKey = new Map(state.words.map((w) => [w.word, w]));

  state.missingRefs = [];
  for (const w of state.words) {
    for (const tag of ["混", "近"]) {
      for (const t of w.tags[tag] || []) {
        if (!state.byKey.has(t)) state.missingRefs.push({ from: w.word, tag, target: t });
      }
    }
  }

  const fam = new Map();
  for (const w of state.words) {
    for (const f of w.tags.族 || []) {
      if (!fam.has(f)) fam.set(f, new Set());
      fam.get(f).add(w.word);
    }
  }
  for (const [f, set] of fam) if (state.byKey.has(f)) set.add(f);
  state.families = Array.from(fam.entries())
    .map(([name, set]) => ({ name, words: Array.from(set).filter((x) => state.byKey.has(x)).sort() }))
    .filter((g) => g.words.length >= 2)
    .sort((a, b) => a.name.localeCompare(b.name));
  state.familyByWord = new Map();
  for (const g of state.families) for (const w of g.words) state.familyByWord.set(w, g);

  state.confusable = buildGroups("混");
  state.synonyms = buildGroups("近");
  state.confusableByWord = groupMap(state.confusable);
  state.synonymByWord = groupMap(state.synonyms);

  state.similar = buildSimilar();
  state.suffix = buildSuffix();
  state.rhyme = buildRhyme();
}

function buildGroups(tag) {
  const parent = new Map();
  const find = (x) => {
    let r = x;
    while (parent.get(r) !== r) r = parent.get(r);
    while (parent.get(x) !== r) { const n = parent.get(x); parent.set(x, r); x = n; }
    return r;
  };
  const union = (a, b) => {
    const ra = find(a), rb = find(b);
    if (ra !== rb) parent.set(ra, rb);
  };
  const nodes = new Set();
  for (const w of state.words) {
    for (const t of w.tags[tag] || []) {
      if (!state.byKey.has(t)) continue;
      nodes.add(w.word); nodes.add(t);
      if (!parent.has(w.word)) parent.set(w.word, w.word);
      if (!parent.has(t)) parent.set(t, t);
      union(w.word, t);
    }
  }
  const groups = new Map();
  for (const n of nodes) {
    const r = find(n);
    if (!groups.has(r)) groups.set(r, []);
    groups.get(r).push(n);
  }
  return Array.from(groups.values())
    .filter((g) => g.length >= 2)
    .map((g) => g.sort())
    .sort((a, b) => b.length - a.length);
}
function groupMap(groups) {
  const m = new Map();
  for (const g of groups) for (const w of g) m.set(w, g);
  return m;
}

function levenshtein(a, b, max = 2) {
  if (Math.abs(a.length - b.length) > max) return max + 1;
  const m = a.length, n = b.length;
  let prev = new Array(n + 1);
  for (let j = 0; j <= n; j++) prev[j] = j;
  for (let i = 1; i <= m; i++) {
    const cur = [i];
    let rowMin = i;
    for (let j = 1; j <= n; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
      if (cur[j] < rowMin) rowMin = cur[j];
    }
    if (rowMin > max) return max + 1;
    prev = cur;
  }
  return prev[n];
}

function buildSimilar() {
  const byLen = new Map();
  for (const w of state.words) {
    if (w.word.includes(" ")) continue;
    for (let l = w.word.length - 2; l <= w.word.length + 2; l++) {
      if (!byLen.has(l)) byLen.set(l, []);
      byLen.get(l).push(w.word);
    }
  }
  const map = new Map();
  for (const w of state.words) {
    if (w.word.includes(" ")) continue;
    const cands = new Set();
    for (let l = w.word.length - 2; l <= w.word.length + 2; l++) {
      for (const x of byLen.get(l) || []) if (x !== w.word) cands.add(x);
    }
    const scored = [];
    for (const x of cands) {
      const d = levenshtein(w.word, x, 2);
      if (d <= 2) scored.push([x, d]);
    }
    scored.sort((a, b) => a[1] - b[1] || a[0].localeCompare(b[0]));
    map.set(w.word, scored.slice(0, 8).map((x) => x[0]));
  }
  return map;
}

function buildSuffix() {
  const map = new Map();
  for (const w of state.words) {
    if (w.word.includes(" ")) continue;
    for (const n of [3, 4]) {
      if (w.word.length < n + 1) continue;
      const key = n + ":" + w.word.slice(-n);
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(w.word);
    }
  }
  return map;
}
function sameEnding(word) {
  if (word.includes(" ")) return [];
  for (const n of [4, 3]) {
    if (word.length < n + 1) continue;
    const arr = state.suffix.get(n + ":" + word.slice(-n)) || [];
    if (arr.length >= 2) return arr.filter((x) => x !== word);
  }
  return [];
}

function rhymeOf(ipa) {
  const s = String(ipa || "").replace(/\//g, "");
  const i = Math.max(s.lastIndexOf("ˈ"), s.lastIndexOf("ˌ"));
  return i >= 0 ? s.slice(i + 1) : s.slice(-3);
}
function buildRhyme() {
  const map = new Map();
  for (const w of state.words) {
    if (!w.ipa) continue;
    const key = rhymeOf(w.ipa);
    if (!key) continue;
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(w.word);
  }
  return map;
}
function sameRhyme(word) {
  const w = state.byKey.get(word);
  if (!w || !w.ipa) return [];
  return (state.rhyme.get(rhymeOf(w.ipa)) || []).filter((x) => x !== word).slice(0, 8);
}

// ---------------------------------------------------------------------------
// 朗读
// ---------------------------------------------------------------------------
let voice = null;
function hasTTS() {
  return typeof speechSynthesis !== "undefined" && typeof SpeechSynthesisUtterance !== "undefined";
}
function pickVoice() {
  if (!hasTTS()) return;
  const vs = speechSynthesis.getVoices();
  voice = vs.find((v) => /^en[-_]/i.test(v.lang) && /Samantha|Aria|Google US English/i.test(v.name))
    || vs.find((v) => /^en[-_]US/i.test(v.lang))
    || vs.find((v) => /^en/i.test(v.lang))
    || null;
}
function speak(text) {
  if (!hasTTS()) { toast("这个浏览器不支持朗读"); return; }
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-US";
  u.rate = 0.88;
  if (voice) u.voice = voice;
  speechSynthesis.speak(u);
}
if (hasTTS()) {
  pickVoice();
  speechSynthesis.onvoiceschanged = pickVoice;
}

// ---------------------------------------------------------------------------
// 路由
// ---------------------------------------------------------------------------
function currentRoute() {
  const raw = location.hash.replace(/^#\/?/, "");
  const parts = raw.split("/");
  return { tab: parts[0] || "review", rest: parts.slice(1) };
}
function go(hash) {
  if (location.hash === hash) renderRoute();
  else location.hash = hash;
}
function renderRoute() {
  if (!state.loaded) return;
  const { tab, rest } = currentRoute();
  const active = tab === "w" ? "words" : tab;
  $$(".tabs a, .tabbar a").forEach((a) => a.classList.toggle("active", a.dataset.tab === active));
  const app = $("#app");
  if (tab === "w") return renderDetail(app, decodeURIComponent(rest[0] || ""));
  if (tab === "relations") return renderRelations(app);
  if (tab === "review") return renderReview(app);
  if (tab === "data") return renderData(app);
  return renderWords(app);
}
function updateBadges() {
  if (!state.loaded) return;
  const due = dueWords().length;
  const examDays = Math.max(0, daysUntil(EXAM_DATE));
  const ed = $("#exam-days");
  if (ed) ed.textContent = examDays;
  const sub = $("#subtitle");
  if (sub) sub.textContent = `${state.words.length} 词 · 到期 ${due} · ${Object.keys(state.progress.words).length} 已学`;
}

// ---------------------------------------------------------------------------
// 词库视图
// ---------------------------------------------------------------------------
function filterChip(key, label) {
  return `<button class="filter ${state.list.filter === key ? "active" : ""}" data-filter="${key}">${label}</button>`;
}

function letterBar() {
  const present = new Set(state.words.map((w) => w.word[0].toUpperCase()));
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
  return `<button class="letter ${state.list.letter === "" ? "active" : ""}" data-letter="">全部</button>`
    + letters.map((L) => `<button class="letter ${state.list.letter === L ? "active" : ""} ${present.has(L) ? "" : "off"}" data-letter="${L}" ${present.has(L) ? "" : "disabled"}>${L}</button>`).join("");
}

function groupedWordCards(list) {
  let out = "";
  let letter = "";
  for (const w of list) {
    const L = w.word[0].toUpperCase();
    if (L !== letter) {
      letter = L;
      out += `<div class="letter-head">${L}</div>`;
    }
    out += wordCard(w);
  }
  return out;
}

function renderWords(app) {
  app.innerHTML = `
    <div class="toolbar">
      <div class="filters" id="filters">
        ${filterChip("all", "全部")}
        ${filterChip("due", "今日到期")}
        ${filterChip("new", "未学")}
        ${filterChip("hard", "易错")}
        ${filterChip("confusable", "有易混")}
        ${filterChip("family", "有词族")}
      </div>
      <div class="letter-bar" id="letter-bar">${letterBar()}</div>
      <div class="result-line">
        <span id="result-count"></span>
        <select id="sort" aria-label="排序">
          <option value="alpha">字母</option>
          <option value="due">到期优先</option>
          <option value="hard">错误最多</option>
          <option value="box">掌握最低</option>
        </select>
      </div>
    </div>
    <div id="word-list" class="grid"></div>
  `;
  $("#sort").value = state.list.sort;
  $("#filters").addEventListener("click", (e) => {
    const b = e.target.closest("[data-filter]");
    if (!b) return;
    state.list.filter = b.dataset.filter;
    $$("#filters .filter").forEach((x) => x.classList.toggle("active", x.dataset.filter === state.list.filter));
    renderWordList();
  });
  $("#letter-bar").addEventListener("click", (e) => {
    const b = e.target.closest("[data-letter]");
    if (!b || b.disabled) return;
    state.list.letter = b.dataset.letter;
    $$("#letter-bar .letter").forEach((x) => x.classList.toggle("active", x.dataset.letter === state.list.letter));
    window.scrollTo(0, 0);
    renderWordList();
  });
  $("#sort").addEventListener("change", (e) => {
    state.list.sort = e.target.value;
    renderWordList();
  });
  renderWordList();
}

function renderWordList() {
  const q = state.list.q.toLowerCase();
  const today = todayStr();
  const list = state.words.filter((w) => {
    if (q) {
      const hay = [w.word, w.ipa, ...w.senses.map((s) => s.gloss), ...w.notes.map((n) => n.text), ...Object.values(w.tags).flat()].join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    if (state.list.letter && w.word[0].toUpperCase() !== state.list.letter) return false;
    const p = getP(w.word);
    switch (state.list.filter) {
      case "due": return p && p.box > 0 && p.due <= today;
      case "new": return !p;
      case "hard": return p && (p.wrong > p.right || p.box <= 2);
      case "confusable": return (w.tags.混 || []).length > 0;
      case "family": return (w.tags.族 || []).length > 0;
      default: return true;
    }
  });

  const cmps = {
    alpha: (a, b) => a.word.localeCompare(b.word),
    due: (a, b) => {
      const pa = getP(a.word), pb = getP(b.word);
      return (pa?.due || "9999-99-99").localeCompare(pb?.due || "9999-99-99") || a.word.localeCompare(b.word);
    },
    hard: (a, b) => {
      const pa = getP(a.word), pb = getP(b.word);
      const sa = (pa?.wrong || 0) - (pa?.right || 0);
      const sb = (pb?.wrong || 0) - (pb?.right || 0);
      return sb - sa || a.word.localeCompare(b.word);
    },
    box: (a, b) => {
      const pa = getP(a.word), pb = getP(b.word);
      return (pa?.box || 0) - (pb?.box || 0) || ((pb?.wrong || 0) - (pa?.wrong || 0)) || a.word.localeCompare(b.word);
    },
  };
  list.sort(cmps[state.list.sort] || cmps.alpha);
  if (q) {
    const rank = (w) => w.word.toLowerCase() === q ? 0 : w.word.toLowerCase().startsWith(q) ? 1 : 2;
    list.sort((a, b) => rank(a) - rank(b));
  }

  const count = $("#result-count");
  if (count) count.textContent = `${state.list.letter ? state.list.letter + " · " : ""}${list.length} 词`;
  const box = $("#word-list");
  if (box) {
    if (!list.length) {
      box.innerHTML = `<div class="panel" style="grid-column:1/-1">没有匹配的词。换个关键词或筛选。</div>`;
    } else {
      box.innerHTML = state.list.sort === "alpha"
        ? groupedWordCards(list)
        : list.map(wordCard).join("");
    }
  }
}

function wordCard(w) {
  const p = getP(w.word);
  const n = p ? p.box : 0;
  const gloss = shortGloss(w.senses.map((s) => s.gloss).join("；"), 52);
  const tags = [...(w.tags.混 || []), ...(w.tags.近 || [])].slice(0, 3);
  return `<article class="word-card" data-word="${esc(w.word)}">
    <div class="wc-top">
      <div class="wc-word">${esc(w.word)}</div>
      ${w.senses[0]?.pos ? `<span class="pos">${esc(w.senses[0].pos)}</span>` : ""}
      <button class="icon-btn" data-speak="${esc(w.word)}" aria-label="朗读 ${esc(w.word)}">${icon("speaker")}</button>
    </div>
    ${w.ipa ? `<div class="ipa">${esc(w.ipa)}</div>` : ""}
    <p class="gloss">${esc(gloss)}</p>
    <div class="wc-foot">
      ${n ? `<span class="box-dot box-${n}">盒 ${n}</span>` : ""}
      ${tags.map((t) => `<span class="chip">${esc(t)}</span>`).join("")}
    </div>
  </article>`;
}

// ---------------------------------------------------------------------------
// 详情
// ---------------------------------------------------------------------------
function relationChip(x) {
  const w = state.byKey.get(x);
  const gloss = w ? shortGloss(w.senses.map((s) => s.gloss).join("；"), 22) : "";
  return `<button class="chip-btn relation-chip" data-word="${esc(x)}">
    <span class="rc-word">${esc(x)}</span>
    ${w?.ipa ? `<span class="rc-ipa">${esc(w.ipa)}</span>` : ""}
    ${gloss ? `<span class="rc-gloss">${esc(gloss)}</span>` : ""}
  </button>`;
}

function renderDetail(app, word) {
  const w = state.byKey.get(word);
  if (!w) {
    app.innerHTML = `<div class="empty"><h2>没有这个词</h2><p><span class="mono">${esc(word)}</span> 不在词库里。</p><p><a class="btn" href="#/words">回词库</a></p></div>`;
    return;
  }
  if (!state.wordBack && state.wordCurrent && state.wordCurrent !== w.word) {
    state.wordStack.push(state.wordCurrent);
    if (state.wordStack.length > 20) state.wordStack.shift();
  }
  state.wordBack = false;
  state.wordCurrent = w.word;
  const prevWord = state.wordStack.length && state.wordStack[state.wordStack.length - 1] !== w.word
    ? state.wordStack[state.wordStack.length - 1]
    : null;
  const p = getP(w.word);
  const fam = state.familyByWord.get(w.word);
  const conf = (state.confusableByWord.get(w.word) || []).filter((x) => x !== w.word);
  const syn = (state.synonymByWord.get(w.word) || []).filter((x) => x !== w.word);
  const sim = (state.similar.get(w.word) || []).slice(0, 8);
  const end = sameEnding(w.word).slice(0, 8);
  const rhy = sameRhyme(w.word);

  app.innerHTML = `<div class="detail">
    <div class="detail-nav">
      <a class="back" href="#/words">${icon("back")} 回词库</a>
      ${prevWord ? `<button class="back-word" id="back-word" type="button">${icon("back")} 返回 ${esc(prevWord)}</button>` : ""}
    </div>
    <div class="detail-head">
      <div style="min-width:0">
        <div class="detail-word">${esc(w.word)}</div>
        <div class="detail-meta">
          ${w.ipa ? `<span class="ipa">${esc(w.ipa)}</span>` : ""}
          ${w.notes.some((n) => n.type === "变形") ? `<span class="chip">${esc(w.notes.find((n) => n.type === "变形").text)}</span>` : ""}
        </div>
      </div>
      <button class="icon-btn" data-speak="${esc(w.word)}" aria-label="朗读">${icon("speaker")}</button>
    </div>
    <div class="sense-list">
      ${w.senses.map((s) => `<div class="sense">${s.pos ? `<span class="pos">${esc(s.pos)}</span>` : ""}<span>${esc(s.gloss)}</span></div>`).join("")}
    </div>
    ${w.notes.map((n) => `<div class="note-block"><span class="note-label ${esc(n.type)}">${esc(n.type)}</span>${esc(n.text)}</div>`).join("")}
    ${conf.length ? `<div class="section-title">易混组</div><div class="chip-row">${conf.map(relationChip).join("")}</div>` : ""}
    ${syn.length ? `<div class="section-title">近义组</div><div class="chip-row">${syn.map(relationChip).join("")}</div>` : ""}
    ${fam ? `<div class="section-title">词族 <span class="mono">${esc(fam.name)}</span></div><div class="chip-row">${fam.words.map(relationChip).join("")}</div>` : ""}
    ${sim.length ? `<div class="section-title">形近词（自动）</div><div class="chip-row">${sim.map(relationChip).join("")}</div>` : ""}
    ${end.length ? `<div class="section-title">同尾词</div><div class="chip-row">${end.map(relationChip).join("")}</div>` : ""}
    ${rhy.length ? `<div class="section-title">同韵词</div><div class="chip-row">${rhy.map(relationChip).join("")}</div>` : ""}
    <div class="status-card">
      <span class="box-dot box-${p?.box || 0}">${p ? "盒子 " + p.box : "未学"}</span>
      ${p?.due ? `<span>下次 ${esc(p.due)}</span>` : ""}
      ${p ? `<span>对 ${p.right || 0} · 错 ${p.wrong || 0}</span>` : ""}
    </div>
    <div class="actions">
      <button class="btn primary" data-mark="known" data-word-mark="${esc(w.word)}">认识</button>
      <button class="btn" data-mark="fuzzy" data-word-mark="${esc(w.word)}">模糊</button>
      <button class="btn danger" data-mark="unknown" data-word-mark="${esc(w.word)}">不认识</button>
      <button class="btn ghost" data-speak="${esc(w.word)}">${icon("speaker")} 朗读</button>
    </div>
  </div>`;

  $("#back-word")?.addEventListener("click", () => {
    if (!state.wordStack.length) return;
    const prev = state.wordStack.pop();
    state.wordBack = true;
    go("#/w/" + encodeURIComponent(prev));
  });
}

// ---------------------------------------------------------------------------
// 关系
// ---------------------------------------------------------------------------
function renderRelations(app) {
  const tab = state.relTab || "mix";
  const tabs = [
    { key: "mix", label: "易混组", count: state.confusable.length },
    { key: "family", label: "词族", count: state.families.length },
    { key: "syn", label: "近义组", count: state.synonyms.length },
  ];
  app.innerHTML = `
    <div class="review-hero">
      <h1>关系</h1>
      <p>易混组来自 <span class="mono">[混:]</span>，词族来自 <span class="mono">[族:]</span>，近义组来自 <span class="mono">[近:]</span>。</p>
      <div class="review-stats">
        ${tabs.map((t) => `<button class="stat ${tab === t.key ? "active" : ""}" data-rel="${t.key}"><b>${t.count}</b><span>${t.label}</span></button>`).join("")}
      </div>
    </div>
    ${tab === "mix" ? `
      <div class="section-title">易混擂台</div>
      <div class="grid">${state.confusable.slice(0, 50).map((g) => groupCard(g, "混")).join("") || `<div class="panel">还没有易混组。在词条行尾加 <span class="mono">[混:xxx]</span> 就会自动成组。</div>`}</div>
    ` : ""}
    ${tab === "family" ? `
      <div class="section-title">词族</div>
      <div class="grid">${state.families.map(familyCard).join("") || `<div class="panel">还没有词族。</div>`}</div>
    ` : ""}
    ${tab === "syn" ? `
      <div class="section-title">近义组</div>
      <div class="grid">${state.synonyms.slice(0, 40).map((g) => groupCard(g, "近")).join("") || `<div class="panel">还没有近义组。</div>`}</div>
    ` : ""}
  `;
}

function groupCard(g, kind) {
  return `<div class="panel">
    <h2>${g.slice(0, 3).map((x) => esc(x)).join(" · ")} <span class="chip ${kind === "混" ? "amber" : "accent"}">${kind}</span></h2>
    ${g.map((x) => {
      const w = state.byKey.get(x);
      return `<div class="kv" data-word="${esc(x)}" style="cursor:pointer">
        <span><strong>${esc(x)}</strong> ${w?.ipa ? `<span class="ipa">${esc(w.ipa)}</span>` : ""}</span>
        <span style="text-align:right;max-width:58%">${esc(shortGloss(w?.senses.map((s) => s.gloss).join("；") || "", 30))}</span>
      </div>`;
    }).join("")}
  </div>`;
}

function familyCard(g) {
  return `<div class="panel">
    <h2><span class="mono">${esc(g.name)}</span> <span class="chip">${g.words.length} 词</span></h2>
    ${g.words.map((x) => {
      const w = state.byKey.get(x);
      return `<div class="kv" data-word="${esc(x)}" style="cursor:pointer">
        <span><strong>${esc(x)}</strong> ${w?.ipa ? `<span class="ipa">${esc(w.ipa)}</span>` : ""}</span>
        <span style="text-align:right;max-width:58%">${esc(shortGloss(w?.senses.map((s) => s.gloss).join("；") || "", 34))}</span>
      </div>`;
    }).join("")}
  </div>`;
}

// ---------------------------------------------------------------------------
// 复习
// ---------------------------------------------------------------------------
const MODE_LABELS = {
  mix: "混合复习",
  zh2en: "看中文选单词",
  en2zh: "看单词选中文",
  listen: "听音选词",
  spell: "拼写",
  cloze: "语境填空",
};
function modeLabel(m) { return MODE_LABELS[m] || "练习"; }

function renderReview(app) {
  if (state.session) return renderQuiz(app);
  if (state.summary) return renderSummary(app);

  const due = dueWords().length;
  const fresh = newWords().length;
  const todayCount = todayWordCount();
  const todayMastered = todayMasteredCount();
  const streak = state.progress.streak?.count || 0;
  const dailyReview = reviewTarget();
  const remain = dailyRemaining();
  const doneToday = remain === 0;
  const noWords = due + fresh === 0;
  const blocked = doneToday || noWords;
  const presets = [20, 30, 40, 50];
  const isPreset = presets.includes(dailyReview);
  const week = last7();
  const maxN = Math.max(1, ...week.map((x) => x.n));

  app.innerHTML = `<div class="review-hero">
    <h1>${greeting()}</h1>
    <p>到期 ${due} 个，未学 ${fresh} 个。今天复习 ${todayCount} 个词，掌握 ${todayMastered} 个。</p>
    ${doneToday ? `<p class="review-done">今天已完成 ${todayCount}/${dailyReview} 个词${due > 0 ? `，还有 ${due} 个到期词明天继续` : "，明天再来"}。</p>` : ""}
    <div class="review-stats">
      <button class="stat" data-stat="due"><b>${due}</b><span>今日到期</span></button>
      <button class="stat" data-stat="todayLearned"><b>${todayCount}/${dailyReview}</b><span>今日复习</span></button>
      <button class="stat" data-stat="streak"><b>${streak}</b><span>连续天数</span></button>
    </div>
    <button class="btn primary block" id="start-review" data-mode="mix" ${blocked ? "disabled" : ""}>${doneToday ? "今日已完成" : noWords ? "今天清完了" : "混合复习"}</button>
    <div class="mode-grid">
      <button class="mode-btn" data-mode="listen" ${blocked ? "disabled" : ""}>听音选词</button>
      <button class="mode-btn" data-mode="spell" ${blocked ? "disabled" : ""}>拼写</button>
      <button class="mode-btn" data-mode="zh2en" ${blocked ? "disabled" : ""}>看中文选单词</button>
      <button class="mode-btn" data-mode="en2zh" ${blocked ? "disabled" : ""}>看单词选中文</button>
    </div>
    <p class="mode-hint">${doneToday ? `今天的 ${dailyReview} 个词已完成，明天再来。` : `混合复习：本次最多 ${Math.min(dailyReview, remain)} 个词（先取今日到期，不够再补未学新词），按 看单词选中文 → 看中文选单词 → 听音选词 → 拼写 各过一遍；拼写跳过短语，拼错排到队尾重拼；本轮按错次定盒：0 错盒 5、1 错盒 4、2 错盒 3、3 错盒 2、4 错及以上盒 1。`}</p>
    <div class="section-title">最近 7 天</div>
    <div class="week-bars">${week.map((x) => `<div class="week-bar ${x.today ? "today" : ""}"><b>${x.n || ""}</b><i style="height:${Math.max(3, Math.min(100, (x.n / maxN) * 100))}%"></i><span>${x.label}</span></div>`).join("")}</div>
    <div class="section-title">设置</div>
    <label class="kv"><span>每天复习</span>
      <span class="daily-review-row">
        <select id="daily-review">
          ${presets.map((n) => `<option value="${n}" ${n === dailyReview ? "selected" : ""}>${n}</option>`).join("")}
          <option value="custom" ${isPreset ? "" : "selected"}>自定义</option>
        </select>
        <input id="daily-review-custom" type="number" min="1" max="200" value="${dailyReview}" ${isPreset ? "hidden" : ""} aria-label="自定义每天复习词数">
      </span>
    </label>
  </div>`;

  $$("[data-mode]").forEach((b) => b.addEventListener("click", () => startSession(null, b.dataset.mode)));
  $("#daily-review").addEventListener("change", (e) => {
    if (e.target.value === "custom") {
      const inp = $("#daily-review-custom");
      inp.hidden = false;
      inp.focus();
      inp.select();
      return;
    }
    state.progress.settings.dailyReview = +e.target.value;
    saveProgress();
    renderRoute();
  });
  $("#daily-review-custom").addEventListener("change", (e) => {
    const n = Math.max(1, Math.min(200, parseInt(e.target.value, 10) || DEFAULT_REVIEW));
    state.progress.settings.dailyReview = n;
    saveProgress();
    renderRoute();
  });
  $("#daily-review-custom").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); e.target.blur(); }
  });
}

function last7() {
  const out = [];
  const names = ["日", "一", "二", "三", "四", "五", "六"];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const s = dateStr(d);
    const day = state.progress.days[s];
    const n = day ? (day.words ? Object.keys(day.words).length : (day.reviewed || 0)) : 0;
    out.push({ s, n, label: names[d.getDay()], today: i === 0 });
  }
  return out;
}

function startSession(customQueue, mode = "mix") {
  if (dailyRemaining() <= 0) {
    toast(`今天已完成 ${todayWordCount()}/${reviewTarget()} 个词，明天再来`);
    return;
  }
  const base = (customQueue && customQueue.length ? customQueue : getQueue())
    .map((x) => (typeof x === "string" ? state.byKey.get(x) : x))
    .filter(Boolean);
  if (mode === "listen" && !hasTTS()) {
    toast("这个浏览器不支持朗读，改用看单词选中文");
    mode = "en2zh";
  }

  let queue = [];
  let modes = [];

  if (mode === "mix") {
    const words = base;
    const phases = ["en2zh", "zh2en", "listen", "spell"];
    for (const ph of phases) {
      if (ph === "listen" && !hasTTS()) continue;
      for (const w of words) {
        if (ph === "spell" && w.word.includes(" ")) continue;
        queue.push(w.word);
        modes.push(ph);
      }
    }
    const phrases = words.filter((w) => w.word.includes(" ")).length;
    if (phrases) toast(`拼写阶段跳过 ${phrases} 个短语`);
  } else {
    let words = base;
    let skipped = 0;
    if (mode === "spell") {
      const before = words.length;
      words = words.filter((w) => !w.word.includes(" "));
      skipped = before - words.length;
    }
    queue = words.map((w) => w.word);
    modes = words.map(() => mode);
    if (skipped) toast(`拼写模式跳过 ${skipped} 个短语`);
  }

  if (!queue.length) {
    toast(mode === "spell" ? "没有可拼写的单词" : "今天没有可复习的词了");
    return;
  }

  state.summary = null;
  state.session = {
    queue,
    modes,
    index: 0, correct: 0, wrong: 0,
    answered: false, q: null, ok: null, choice: undefined, spoken: false,
    mode,
    mixWrong: new Map(),
  };
  state.session.q = makeQuestion(state.byKey.get(queue[0]), modes[0]);
  go("#/review");
  renderRoute();
}

function renderSummary(app) {
  const s = state.summary;
  const remain = dailyRemaining();
  const doneToday = remain === 0;
  const todayCount = todayWordCount();
  const dailyReview = reviewTarget();
  app.innerHTML = `<div class="review-hero">
    <h1>${esc(modeLabel(s.mode))}完成</h1>
    <p>今天复习 ${todayCount} 个词，共 ${s.total} 次作答，答对 ${s.correct} 次，答错 ${s.wrong} 次。</p>
    ${doneToday ? `<p class="review-done">今天已完成 ${todayCount}/${dailyReview} 个词，明天再来。</p>` : `<p>今天还可复习 ${remain} 个词。</p>`}
    <div class="review-stats">
      <div class="stat"><b>${s.correct}</b><span>答对次数</span></div>
      <div class="stat"><b>${s.wrong}</b><span>答错次数</span></div>
      <div class="stat"><b>${Math.round((s.correct / Math.max(1, s.total)) * 100)}%</b><span>正确率（按次数）</span></div>
    </div>
    <div class="actions">
      <button class="btn primary block" id="again" ${doneToday ? "disabled" : ""}>${doneToday ? "今日已完成" : "再来一组"}</button>
      <button class="btn block" id="to-words">回词库</button>
    </div>
  </div>`;
  $("#again").addEventListener("click", () => {
    if (dailyRemaining() <= 0) { toast(`今天已完成 ${todayWordCount()}/${reviewTarget()} 个词，明天再来`); return; }
    state.summary = null;
    startSession(null, s.mode);
  });
  $("#to-words").addEventListener("click", () => { state.summary = null; go("#/words"); });
}

// ---------------------------------------------------------------------------
// 出题
// ---------------------------------------------------------------------------
function distractors(w, n = 3) {
  const out = [];
  const add = (x) => {
    if (x && x !== w.word && !out.includes(x) && state.byKey.has(x)) out.push(x);
  };
  const conf = shuffle(state.confusableByWord.get(w.word) || []);
  const fam = shuffle(state.familyByWord.get(w.word)?.words || []);
  const sim = shuffle(state.similar.get(w.word) || []);
  for (const x of conf) add(x);
  for (const x of fam) add(x);
  for (const x of sim) add(x);
  if (out.length < n) {
    const same = state.words.filter((x) =>
      x.word !== w.word &&
      x.senses[0]?.pos === w.senses[0]?.pos &&
      Math.abs(x.word.length - w.word.length) <= 2
    );
    for (const x of shuffle(same)) add(x.word);
  }
  if (out.length < n) for (const x of shuffle(state.words)) add(x.word);
  return out.slice(0, n);
}

function firstPos(word) {
  return state.byKey.get(word)?.senses[0]?.pos || "";
}
function optionLabel(word, text) {
  const pos = firstPos(word);
  return pos ? pos + ". " + text : text;
}

function makeQuestion(w, mode = "mix") {
  if (!w) return null;
  const gloss = w.senses.map((s) => s.gloss).join("；");
  const example = w.notes.find((n) => n.type === "例" && new RegExp(escapeReg(w.word), "i").test(n.text));
  let type;
  if (mode === "mix") {
    const types = ["zh2en", "en2zh"];
    if (hasTTS()) types.push("listen");
    if (!w.word.includes(" ")) types.push("spell");
    if (example) types.push("cloze");
    type = types[Math.floor(Math.random() * types.length)];
  } else if (mode === "spell" && !w.word.includes(" ")) {
    type = "spell";
  } else if (mode === "listen" && hasTTS()) {
    type = "listen";
  } else if (mode === "cloze" && example) {
    type = "cloze";
  } else if (mode === "en2zh") {
    type = "en2zh";
  } else {
    type = "zh2en";
  }
  const ds = distractors(w, 3);

  if (type === "en2zh") {
    const correct = shortGloss(gloss, 42);
    const labels = [{ label: correct, word: w.word }];
    for (const d of ds) {
      const dw = state.byKey.get(d);
      const g = shortGloss(dw?.senses.map((s) => s.gloss).join("；") || "", 42);
      if (g && !labels.some((x) => x.label === g)) labels.push({ label: g, word: d });
    }
    if (labels.length < 4) {
      for (const x of shuffle(state.words)) {
        const g = shortGloss(x.senses.map((s) => s.gloss).join("；") || "", 42);
        if (g && !labels.some((y) => y.label === g)) labels.push({ label: g, word: x.word });
        if (labels.length >= 4) break;
      }
    }
    return {
      type,
      prompt: w.word,
      options: shuffle(labels.map((x) => ({ key: x.label, label: optionLabel(x.word, x.label), word: x.word }))),
      answer: correct,
    };
  }

  if (type === "spell") {
    const hint = w.word.split("").map((c, i) => (i === 0 || c === " " || c === "-" || c === "'" ? c : "_")).join(" ");
    return { type, prompt: gloss, hint, answer: w.word, options: [] };
  }

  if (type === "cloze" && example) {
    const sentence = example.text.replace(new RegExp(escapeReg(w.word), "gi"), "_____");
    return {
      type,
      prompt: sentence,
      options: shuffle([w.word, ...ds]).map((x) => ({ key: x, label: optionLabel(x, x), word: x })),
      answer: w.word,
    };
  }

  if (type === "listen") {
    return {
      type,
      prompt: "",
      options: shuffle([w.word, ...ds]).map((x) => ({ key: x, label: optionLabel(x, x), word: x })),
      answer: w.word,
    };
  }

  return {
    type: "zh2en",
    prompt: shortGloss(gloss, 60),
    options: shuffle([w.word, ...ds]).map((x) => ({ key: x, label: optionLabel(x, x), word: x })),
    answer: w.word,
  };
}

// ---------------------------------------------------------------------------
// 答题视图
// ---------------------------------------------------------------------------
function renderQuiz(app) {
  const s = state.session;
  const w = state.byKey.get(s.queue[s.index]);
  if (!w) { finishSession(); return; }
  if (!s.q) s.q = makeQuestion(w, (s.modes && s.modes[s.index]) || s.mode);
  const q = s.q;
  if (!q) { finishSession(); return; }

  const pct = Math.round((s.index / s.queue.length) * 100);
  const label = modeLabel(q.type);
  const spellWrongs = mixWrongCount(w.word);
  const spellBox = mixBox(w.word);

  let prompt = "";
  if (q.type === "en2zh") {
    prompt = `<div class="quiz-prompt"><span class="big">${esc(w.word)}</span> ${w.ipa ? `<span class="ipa">${esc(w.ipa)}</span>` : ""}<div style="margin-top:10px"><button class="btn ghost" data-speak="${esc(w.word)}">${icon("speaker")} 朗读</button></div></div>`;
  } else if (q.type === "listen") {
    prompt = `<div class="quiz-prompt"><button class="btn primary" data-speak="${esc(w.word)}">${icon("speaker")} 再听一遍</button><p style="font-size:13px;color:var(--muted);margin:10px 0 0">听发音，选出你听到的词</p></div>`;
  } else if (q.type === "spell") {
    prompt = `<div class="quiz-prompt">${esc(shortGloss(w.senses.map((x) => x.gloss).join("；"), 60))}${w.ipa ? `<div class="ipa">${esc(w.ipa)}</div>` : ""}<p class="mono" style="letter-spacing:.14em;margin:10px 0 0">${esc(q.hint)}</p></div>`;
  } else {
    prompt = `<div class="quiz-prompt">${esc(q.prompt)}</div>`;
  }

  let opts = "";
  if (q.type === "spell") {
    opts = s.answered ? "" : `<div class="answer-input"><input id="spell-input" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="输入单词"><button class="btn primary" id="spell-submit">检查</button></div>`;
  } else {
    opts = `<div class="options">${q.options.map((o, i) => {
      let cls = "option";
      if (s.answered) {
        if (String(o.key) === String(q.answer)) cls += " correct";
        else if (String(o.key) === String(s.choice)) cls += " wrong";
      }
      return `<button class="${cls}" data-option="${esc(o.key)}" ${s.answered ? "disabled" : ""}><span class="key">${i + 1}</span><span>${esc(o.label)}</span></button>`;
    }).join("")}</div>`;
  }

  let feedback = "";
  if (s.answered) {
    feedback = `<div class="feedback">
      <h3 class="${s.ok ? "ok" : "no"}">${s.ok ? "对了" : "再看一眼"}</h3>
      <div class="word-line"><strong>${esc(w.word)}</strong>${w.ipa ? `<span class="ipa">${esc(w.ipa)}</span>` : ""}<button class="icon-btn" data-speak="${esc(w.word)}" aria-label="朗读">${icon("speaker")}</button><a class="chip-btn" href="#/w/${encodeURIComponent(w.word)}" target="_blank" rel="noopener" title="在新窗口打开词条">查看词条</a></div>
      <div class="sense-list" style="margin:8px 0">${w.senses.map((x) => `<div class="sense">${x.pos ? `<span class="pos">${esc(x.pos)}</span>` : ""}<span>${esc(x.gloss)}</span></div>`).join("")}</div>
      ${w.notes.map((n) => `<div class="note-block"><span class="note-label ${esc(n.type)}">${esc(n.type)}</span>${esc(n.text)}</div>`).join("")}
      ${q.options.length ? `<div class="section-title">选项解析</div><div class="option-review">${q.options.map((o) => {
        const ow = state.byKey.get(o.word || o.key);
        if (!ow) return "";
        const isCorrect = String(o.key) === String(q.answer);
        const isChoice = String(o.key) === String(s.choice);
        return `<a class="option-review-row ${isCorrect ? "correct" : ""} ${isChoice && !isCorrect ? "wrong" : ""}" href="#/w/${encodeURIComponent(ow.word)}" target="_blank" rel="noopener" title="在新窗口打开词条">
          <span class="or-word">${esc(ow.word)}</span>
          ${ow.ipa ? `<span class="or-ipa">${esc(ow.ipa)}</span>` : ""}
          ${isCorrect ? `<span class="or-badge">答案</span>` : ""}
          <span class="or-gloss">${esc(ow.senses.map((x) => x.gloss).join("；"))}</span>
        </a>`;
      }).join("")}</div>` : ""}
      ${s.mode === "mix" && s.modes && s.modes[s.index] === "spell" ? `<p class="spell-note ${s.ok ? "ok" : "retry"}">${s.ok ? (spellWrongs ? `拼写正确。本轮这个词错了 ${spellWrongs} 次，最终放入盒 ${spellBox}。` : "拼写正确。本轮一次没错，最终放入盒 5。") : `拼写错误，已排到队尾重拼（本轮已错 ${spellWrongs} 次）。`}</p>` : ""}
      <div class="actions"><button class="btn primary block" id="next-q">${s.index + 1 >= s.queue.length ? "看结果" : "下一个"}</button></div>
    </div>`;
  }

  app.innerHTML = `<div class="quiz">
    <div class="quiz-top">
      <span>${s.index + 1} / ${s.queue.length} · ${label}</span>
      <button class="btn ghost" id="exit-review">结束</button>
    </div>
    <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
    <div class="quiz-card">
      <div class="quiz-type">${label}</div>
      ${prompt}
      ${opts}
      ${feedback}
    </div>
  </div>`;

  $("#exit-review").addEventListener("click", () => {
    if (confirm("结束本轮？已答的会保留。")) {
      state.session = null;
      renderRoute();
    }
  });
  $$("[data-option]", app).forEach((b) => b.addEventListener("click", () => answerChoice(b.dataset.option)));
  const next = $("#next-q");
  if (next) next.addEventListener("click", nextQuestion);
  if (q.type === "spell" && !s.answered) {
    const input = $("#spell-input");
    input.focus();
    $("#spell-submit").addEventListener("click", answerSpell);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") answerSpell(); });
  }
  if (q.type === "listen" && !s.answered && !s.spoken) {
    s.spoken = true;
    setTimeout(() => speak(w.word), 220);
  }
  if (s.answered) {
    setTimeout(() => {
      const fb = $(".feedback");
      if (fb) fb.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }, 60);
  }
}

function answerChoice(choice) {
  const s = state.session;
  if (!s || s.answered) return;
  const w = state.byKey.get(s.queue[s.index]);
  const ok = String(choice) === String(s.q.answer);
  s.answered = true;
  s.ok = ok;
  s.choice = choice;
  if (hasTTS()) speak(w.word);
  if (ok) s.correct += 1; else s.wrong += 1;
  gradeWord(w.word, ok);
  trackMixAnswer(w.word, ok);
  updateBadges();
  renderRoute();
}

function answerSpell() {
  const s = state.session;
  if (!s || s.answered) return;
  const w = state.byKey.get(s.queue[s.index]);
  const input = $("#spell-input");
  const val = (input?.value || "").trim().toLowerCase();
  const ok = val === w.word.toLowerCase();
  const isMixSpell = s.mode === "mix" && s.modes && s.modes[s.index] === "spell";

  s.answered = true;
  s.ok = ok;
  s.choice = val;
  if (hasTTS()) speak(w.word);
  if (ok) s.correct += 1; else s.wrong += 1;
  gradeWord(w.word, ok);

  if (isMixSpell && !ok) {
    s.queue.push(w.word);
    s.modes.push("spell");
  }
  if (isMixSpell) trackMixAnswer(w.word, ok);

  updateBadges();
  renderRoute();
}

function nextQuestion() {
  const s = state.session;
  if (!s) return;
  s.index += 1;
  s.answered = false;
  s.ok = null;
  s.choice = undefined;
  s.spoken = false;
  if (s.index >= s.queue.length) { finishSession(); return; }
  s.q = makeQuestion(state.byKey.get(s.queue[s.index]), (s.modes && s.modes[s.index]) || s.mode);
  window.scrollTo(0, 0);
  renderRoute();
}

function finishSession() {
  const s = state.session;
  state.session = null;
  state.summary = { correct: s.correct, wrong: s.wrong, total: s.queue.length, mode: s.mode };
  updateBadges();
  renderRoute();
  if (dailyRemaining() === 0) toast(`今日已完成 ${todayWordCount()}/${reviewTarget()} 个词`);
}

// ---------------------------------------------------------------------------
// 统计详情弹层
// ---------------------------------------------------------------------------
function openModal(title, html) {
  const modal = $("#modal");
  if (!modal) return;
  $("#modal-title").textContent = title;
  $("#modal-body").innerHTML = html;
  modal.hidden = false;
  document.body.classList.add("modal-open");
}
function closeModal() {
  const modal = $("#modal");
  if (!modal) return;
  modal.hidden = true;
  document.body.classList.remove("modal-open");
}
function statWordList(words, metaFn) {
  if (!words.length) return `<p class="stat-empty">没有记录。</p>`;
  const out = words.slice(0, 300).map((item) => {
    const w = state.byKey.get(item.word || item);
    if (!w) return "";
    const meta = metaFn ? metaFn(w) : "";
    return `<div class="kv stat-row" data-word="${esc(w.word)}">
      <span><strong>${esc(w.word)}</strong>${w.ipa ? ` <span class="ipa">${esc(w.ipa)}</span>` : ""}</span>
      <span class="stat-row-right">${esc(shortGloss(w.senses.map((s) => s.gloss).join("；"), 28))}${meta ? `<br><span class="stat-meta">${meta}</span>` : ""}</span>
    </div>`;
  }).join("");
  return out + (words.length > 300 ? `<p class="stat-empty">只显示前 300 个，共 ${words.length} 个。</p>` : "");
}
function showStat(key) {
  const today = todayStr();
  const d = todayStats();
  const tracked = state.words.filter((w) => getP(w.word));
  const todayList = todayWordList();
  const todayCount = todayList.length;
  const todayMastered = todayMasteredCount();
  const masteryRate = todayMasteryRate();
  const meta = (w) => {
    const p = getP(w.word) || {};
    const box = p.box || 0;
    const parts = [];
    if (box) parts.push("盒 " + box);
    parts.push(box >= 4 ? `<span class="mastery-ok">已掌握</span>` : `<span class="mastery-bad">未掌握</span>`);
    if (p.due) parts.push("下次 " + p.due);
    return parts.join(" · ");
  };
  const summary = (html) => `<p class="stat-summary">${html}</p>`;

  if (key === "due") {
    const list = dueWords().sort((a, b) => (getP(a.word)?.due || "").localeCompare(getP(b.word)?.due || ""));
    openModal("今日到期", list.length
      ? summary(`共 ${list.length} 个到期词，按到期时间排序。`) + statWordList(list, meta)
      : summary("今天没有到期词。"));
    return;
  }
  if (key === "todayLearned") {
    openModal("今日复习", summary(`今天复习 ${todayCount} 个词（新学 ${d.new || 0} 个），掌握 ${todayMastered} 个（掌握率 ${masteryRate}%）。每天复习目标 ${reviewTarget()} 个。`) + statWordList(todayList, meta));
    return;
  }
  if (key === "streak") {
    openModal("连续天数", summary(`当前连续 ${state.progress.streak?.count || 0} 天。`)
      + `<div class="kv"><span>${today}（今天）</span><span>复习 ${todayCount} 个词 · 掌握 ${todayMastered} 个</span></div>`);
    return;
  }
  if (key === "total") {
    const counts = {};
    for (const w of state.words) {
      const L = w.word[0].toUpperCase();
      counts[L] = (counts[L] || 0) + 1;
    }
    const ipa = state.words.filter((w) => w.ipa).length;
    const pos = state.words.filter((w) => w.senses.some((s) => s.pos)).length;
    openModal("词条统计", summary(`${state.words.length} 个唯一词；有音标 ${ipa}；有词性 ${pos}；词族 ${state.families.length}；易混组 ${state.confusable.length}；近义组 ${state.synonyms.length}。`)
      + `<div class="letter-counts">${Object.keys(counts).sort().map((L) => `<span class="chip">${L} ${counts[L]}</span>`).join("")}</div>`);
    return;
  }
  if (key === "tracked") {
    openModal("已进复习", summary(`共 ${tracked.length} 个词。`) + statWordList(tracked.slice().sort((a, b) => (getP(a.word)?.box || 0) - (getP(b.word)?.box || 0)), meta));
    return;
  }
  if (key === "known") {
    const list = state.words.filter((w) => (getP(w.word)?.box || 0) >= 4);
    openModal("掌握（盒 4+）", summary(`共 ${list.length} 个词。`) + statWordList(list, meta));
    return;
  }
  if (key === "reviewedToday") {
    openModal("今日复习", summary(`今天复习 ${todayCount} 个词，掌握 ${todayMastered} 个，掌握率 ${masteryRate}%。`) + statWordList(todayList, meta));
    return;
  }
  if (key === "accuracyToday") {
    openModal("今日掌握率", summary(`今天复习 ${todayCount} 个词，掌握 ${todayMastered} 个，掌握率 ${masteryRate}%。下面是今天复习过的词。`) + statWordList(todayList, meta));
  }
}

// ---------------------------------------------------------------------------
// 数据
// ---------------------------------------------------------------------------
function renderData(app) {
  const total = state.words.length;
  const withP = Object.keys(state.progress.words).length;
  const known = state.words.filter((w) => (getP(w.word)?.box || 0) >= 4).length;
  const due = dueWords().length;
  const todayCount = todayWordCount();
  const masteryRate = todayMasteryRate();
  const noPos = state.words.filter((w) => !w.senses.some((s) => s.pos)).length;

  app.innerHTML = `
    <div class="stat-grid">
      <button class="stat" data-stat="total"><b>${total}</b><span>词条</span></button>
      <button class="stat" data-stat="tracked"><b>${withP}</b><span>已进复习</span></button>
      <button class="stat" data-stat="known"><b>${known}</b><span>掌握（盒 4+）</span></button>
      <button class="stat" data-stat="due"><b>${due}</b><span>今日到期</span></button>
      <button class="stat" data-stat="reviewedToday"><b>${todayCount}</b><span>今日复习（词）</span></button>
      <button class="stat" data-stat="accuracyToday"><b>${masteryRate}%</b><span>今日掌握率</span></button>
    </div>
    <div class="panel">
      <h2>盒子怎么运作</h2>
      <p>盒子是间隔复习的等级，1–5 盒。</p>
      <table class="box-table">
        <thead><tr><th>盒子</th><th>下次复习</th></tr></thead>
        <tbody>
          <tr><td>1</td><td>1 天后</td></tr>
          <tr><td>2</td><td>2 天后</td></tr>
          <tr><td>3</td><td>4 天后</td></tr>
          <tr><td>4</td><td>7 天后</td></tr>
          <tr><td>5</td><td>14 天后</td></tr>
        </tbody>
      </table>
      <p><strong>规则：</strong></p>
      <ul class="box-rules">
        <li>新词：还没有盒子；第一次答对 → 盒 2（2 天后再见）；第一次答错 → 盒 1（明天再见）</li>
        <li>答对：盒子 +1，最高盒 5</li>
        <li>答错：直接回到盒 1，明天再来</li>
        <li>盒 4、5 算掌握，也就是“掌握（盒 4+）”</li>
        <li>今日掌握率 = 今天复习的词里，盒 4/5 的比例</li>
      </ul>
      <p><strong>混合复习的定盒规则：</strong></p>
      <ul class="box-rules">
        <li>混合复习的 4 个阶段会临时改变盒子，最终按本轮错次重新定盒。</li>
        <li>按这个单词本轮答错的次数定盒：一次不错 → 盒 5；错 1 次 → 盒 4；错 2 次 → 盒 3；错 3 次 → 盒 2；错 4 次及以上 → 盒 1。</li>
        <li>拼写错了会排到队尾重拼；重拼正确后，仍按本轮总错次定盒。</li>
        <li>手动“认识” = 盒 5、14 天；“模糊” = 盒 2、明天；“不认识” = 盒 1、明天。</li>
      </ul>
    </div>
    <div class="panel">
      <h2>形近词 / 同尾词 / 同韵词怎么来的</h2>
      <p>这三类由程序自动生成，不需要写标签，只在词条详情页展示；其中形近词还会参与选择题干扰项的抽取。</p>
      <table class="box-table">
        <thead><tr><th>类型</th><th>生成方式</th></tr></thead>
        <tbody>
          <tr><td>形近词</td><td>只比较不含空格的单词；长度差 ≤ 2，编辑距离 ≤ 2；按编辑距离、字母顺序取前 8 个。</td></tr>
          <tr><td>同尾词</td><td>优先取最后 4 个字母；同组不足 2 个词时退到最后 3 个字母；仍不足 2 个就不显示；最多 8 个。</td></tr>
          <tr><td>同韵词</td><td>取音标最后一个重音符号之后的部分；没有重音就取最后 3 个字符；同组最多 8 个；没有音标的词不显示。</td></tr>
        </tbody>
      </table>
      <ul class="box-rules">
        <li>同尾词、同韵词只是拼写/发音上的粗略相似，不等于构词关系；构词关系仍然看 <span class="mono">[族:]</span>。</li>
        <li>例：<span class="mono">absent</span> 和 <span class="mono">absence</span> 会互相出现在形近词里；同尾词分别落在 <span class="mono">-ent</span> 和 <span class="mono">-ence</span>，同韵词也不同，所以不会互相出现在这两类里。</li>
      </ul>
    </div>
    <div class="panel">
      <h2>词库文件</h2>
      <p>本地直接打开时，词库会缓存在这个浏览器里。改了 words.md 后，点下面重新选一次；部署到 GitHub Pages 后会自动读取最新文件。</p>
      <label class="btn" style="display:inline-flex;align-items:center;gap:6px;cursor:pointer">${icon("upload")} 重新选择 words.md<input type="file" id="reload-md" accept=".md,.txt" hidden></label>
    </div>
    <div class="panel">
      <h2>进度备份</h2>
      <p>进度存在这台设备的浏览器里。换设备或清缓存前，先导出。</p>
      <div class="actions">
        <button class="btn primary" id="export">${icon("download")} 导出 JSON</button>
        <label class="btn" style="display:inline-flex;align-items:center;gap:6px;cursor:pointer">${icon("upload")} 导入<input type="file" id="import" accept="application/json" hidden></label>
        <button class="btn danger" id="reset">${icon("trash")} 清空进度</button>
      </div>
    </div>
    <div class="panel">
      <h2>格式检查</h2>
      <div class="kv"><span>无法解析的行</span><span>${state.badLines.length}</span></div>
      <div class="kv"><span>重复词头</span><span>${state.dupes.length}</span></div>
      <div class="kv"><span>引用了但不存在的词</span><span>${state.missingRefs.length}</span></div>
      <div class="kv"><span>缺词性</span><span>${noPos}</span></div>
      ${state.badLines.length ? `<details><summary>查看无法解析的行</summary><ul class="warn-list">${state.badLines.slice(0, 50).map((x) => `<li class="mono">${esc(x)}</li>`).join("")}</ul></details>` : ""}
      ${state.missingRefs.length ? `<details><summary>查看缺失引用</summary><ul class="warn-list">${state.missingRefs.slice(0, 50).map((x) => `<li><b>${esc(x.from)}</b> 的 [${x.tag}] 指向 <span class="mono">${esc(x.target)}</span>，词库里没有</li>`).join("")}</ul></details>` : ""}
    </div>
    <div class="panel">
      <h2>怎么加词</h2>
      <p>在 <span class="mono">words.md</span> 里加一行：</p>
      <pre class="mono" style="white-space:pre-wrap;background:var(--surface-2);padding:10px;border-radius:8px;overflow:auto">career n. 职业；事业；生涯 /kəˈrɪr/ [族:care] [混:cancer,carrier]</pre>
      <p><span class="mono">[族:x]</span> 词根家族，<span class="mono">[混:a,b]</span> 易混组，<span class="mono">[近:a,b]</span> 近义组。只写一边，程序自动双向补全。补充行用 <span class="mono">- 辨析: …</span>、<span class="mono">- 记: …</span>、<span class="mono">- 错: …</span>。</p>
    </div>
  `;

  $("#export").addEventListener("click", exportProgress);
  $("#import").addEventListener("change", importProgress);
  $("#reload-md").addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      loadData(await file.text());
      toast("词库已更新");
    } catch (err) {
      alert("读取失败：" + err.message);
    } finally {
      e.target.value = "";
    }
  });
  $("#reset").addEventListener("click", () => {
    if (!confirm("确定清空所有复习进度？词库本身不会动。")) return;
    state.progress = freshProgress();
    saveProgress();
    updateBadges();
    renderRoute();
    toast("进度已清空");
  });
}

function exportProgress() {
  const blob = new Blob([JSON.stringify(state.progress, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `cet4-progress-${todayStr()}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  toast("已导出");
}

async function importProgress(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    if (!data || typeof data !== "object" || !data.words) throw new Error("格式不对");
    if (!confirm("用这个文件覆盖当前进度？")) return;
    state.progress = migrateProgress(data);
    saveProgress();
    updateBadges();
    renderRoute();
    toast("进度已导入");
  } catch (err) {
    alert("导入失败：" + err.message);
  } finally {
    e.target.value = "";
  }
}

// ---------------------------------------------------------------------------
// 加载
// ---------------------------------------------------------------------------
function loadData(md) {
  const parsed = parseWords(md);
  const deduped = dedupeWords(parsed.words);
  state.words = deduped.words;
  state.badLines = parsed.bad;
  state.dupes = deduped.dupes;
  buildIndexes();
  state.progress = loadProgress();
  const today = todayStr();
  const day = state.progress.days[today];
  if (day && !day.words) {
    const ws = state.words.filter((w) => getP(w.word)?.last === today);
    if (ws.length) {
      day.words = {};
      for (const w of ws) day.words[w.word] = { right: 0, wrong: 0 };
      saveProgress();
    }
  }
  state.loaded = true;
  window.__cet = state;
  try { localStorage.setItem("cet4.md", md); } catch (e) { /* 忽略 */ }
  if (!location.hash) history.replaceState(null, "", "#/review");
  renderRoute();
  updateBadges();
}

function renderPicker(message = "") {
  $("#app").innerHTML = `<div class="empty">
    <h2>先选词库文件</h2>
    <p>${message || "浏览器在本地直接打开时，不允许自动读取 <span class=\"mono\">words.md</span>。点下面选一次；之后这个浏览器（包括新标签页）会记住。清空网站数据后需要再选一次。"}</p>
    <div class="file-drop" id="drop">把 <b>words.md</b> 拖到这里，或点一下选择文件</div>
    <input type="file" id="file" accept=".md,.txt" hidden>
  </div>`;
  const input = $("#file");
  const drop = $("#drop");
  const handle = async (file) => {
    if (!file) return;
    try {
      loadData(await file.text());
    } catch (e) {
      alert("读取失败：" + e.message);
    }
  };
  drop.addEventListener("click", () => input.click());
  input.addEventListener("change", (e) => handle(e.target.files?.[0]));
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("hover"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("hover"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    drop.classList.remove("hover");
    handle(e.dataTransfer.files?.[0]);
  });
}

// ---------------------------------------------------------------------------
// 事件
// ---------------------------------------------------------------------------
function setupTopSearch() {
  const input = $("#search");
  const clear = $("#clear-search");
  if (!input) return;

  const apply = () => {
    state.list.q = input.value.trim();
    state.list.letter = "";
    if (currentRoute().tab !== "words") {
      location.hash = "#/words";
    } else if ($("#word-list")) {
      $$("#letter-bar .letter").forEach((x) => x.classList.toggle("active", x.dataset.letter === ""));
      renderWordList();
    }
  };

  input.addEventListener("input", debounce(apply, 120));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); apply(); }
    if (e.key === "Escape") { input.blur(); }
  });
  clear?.addEventListener("click", () => {
    input.value = "";
    state.list.q = "";
    state.list.letter = "";
    if (currentRoute().tab !== "words") location.hash = "#/words";
    else if ($("#word-list")) {
      $$("#letter-bar .letter").forEach((x) => x.classList.toggle("active", x.dataset.letter === ""));
      renderWordList();
    }
    input.focus();
  });
}

function installGlobalHandlers() {
  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-close-modal]") || e.target.closest("#modal-close")) {
      e.preventDefault();
      closeModal();
      return;
    }
    const relBtn = e.target.closest("[data-rel]");
    if (relBtn) {
      e.preventDefault();
      state.relTab = relBtn.dataset.rel;
      renderRelations($("#app"));
      return;
    }
    const statBtn = e.target.closest("[data-stat]");
    if (statBtn) {
      e.preventDefault();
      showStat(statBtn.dataset.stat);
      return;
    }
    const speakBtn = e.target.closest("[data-speak]");
    if (speakBtn) {
      e.preventDefault();
      e.stopPropagation();
      speak(speakBtn.dataset.speak);
      return;
    }
    const markBtn = e.target.closest("[data-mark]");
    if (markBtn) {
      e.preventDefault();
      markWord(markBtn.dataset.wordMark, markBtn.dataset.mark);
      toast(markBtn.dataset.mark === "known" ? "标为认识" : markBtn.dataset.mark === "fuzzy" ? "标为模糊" : "标为不认识");
      updateBadges();
      renderRoute();
      return;
    }
    const wordEl = e.target.closest("[data-word]");
    if (wordEl) {
      e.preventDefault();
      closeModal();
      go("#/w/" + encodeURIComponent(wordEl.dataset.word));
      return;
    }
    if (e.target.closest("#due-pill")) {
      e.preventDefault();
      go("#/review");
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !$("#modal")?.hidden) closeModal();
  });

  document.addEventListener("keydown", (e) => {
    if (!state.session || currentRoute().tab !== "review") return;
    if (e.target.matches("input, textarea, select")) return;
    if (["1", "2", "3", "4"].includes(e.key)) {
      const btn = $$(".option")[+e.key - 1];
      if (btn && !btn.disabled) btn.click();
    } else if (e.key === "Enter") {
      const next = $("#next-q");
      if (next) { e.preventDefault(); next.click(); }
    } else if (e.key === " ") {
      if (e.target.closest("button")) return;
      const s = state.session;
      const w = s && state.byKey.get(s.queue[s.index]);
      if (w) { e.preventDefault(); speak(w.word); }
    }
  });

  window.addEventListener("storage", (e) => {
    if (e.key === STORE && state.loaded) {
      state.progress = loadProgress();
      updateBadges();
      renderRoute();
    }
  });

  window.addEventListener("hashchange", () => {
    window.scrollTo(0, 0);
    renderRoute();
  });
}

async function init() {
  $$("[data-icon]").forEach((el) => { el.innerHTML = icon(el.dataset.icon); });
  installGlobalHandlers();
  setupTopSearch();
  let md = null;
  let fetchError = "";
  try {
    const r = await fetch("words.md", { cache: "no-store" });
    if (r.ok) md = await r.text();
    else if (r.status === 404) {
      fetchError = "没有找到 words.md。确认它和 index.html 在同一个文件夹，或者手动选一下。";
    }
  } catch (e) { /* file:// 或离线 */ }
  if (!md) {
    try { md = localStorage.getItem("cet4.md"); } catch (e) { /* 忽略 */ }
  }
  if (!md) { renderPicker(fetchError); return; }
  loadData(md);

  if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
}

init().catch((e) => {
  $("#app").innerHTML = `<div class="empty"><h2>加载失败</h2><p class="mono">${esc(e.message)}</p><p>刷新试试。如果一直失败，检查 words.md 格式。</p></div>`;
});
})();
