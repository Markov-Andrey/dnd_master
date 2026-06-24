// core.js — общие утилиты и состояние
const API = "";
let currentNpcId = null;
let inDialogue = false;
let playerData = null;
let currentLocation = null;
let inCombat = false;

const $ = (s) => document.querySelector(s);

async function api(path, method = "GET", body = null) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API}${path}`, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
}

function addMessage(text, role = "system") {
    const el = document.createElement("div");
    el.className = `message ${role}`;
    el.textContent = text;
    const box = $("#messages");
    if (box) { box.appendChild(el); box.scrollTop = box.scrollHeight; }
}

function setStatus(text) {
    const sb = $("#status-bar");
    if (sb) sb.textContent = text;
}
