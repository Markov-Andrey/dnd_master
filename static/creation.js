// creation.js — создание персонажа

const ATTR_COSTS = { 8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9 };
const ATTR_NAMES = { str: "Сила", dex: "Ловкость", con: "Телосложение", int: "Интеллект", wis: "Мудрость", cha: "Харизма" };
let charAttrs = { str: 10, dex: 10, con: 10, int: 10, wis: 10, cha: 10 };

function calcAttrCost(score) {
    let cost = 0;
    for (let i = 8; i < score; i++) {
        cost += i >= 14 ? 2 : 1;
    }
    return cost;
}

function calcTotalCost() {
    return Object.values(charAttrs).reduce((sum, v) => sum + calcAttrCost(v), 0);
}

function renderAttrEditor() {
    const container = $("#attr-editor");
    if (!container) return;
    container.innerHTML = "";
    for (const [key, name] of Object.entries(ATTR_NAMES)) {
        const val = charAttrs[key];
        const mod = Math.floor((val - 10) / 2);
        const row = document.createElement("div");
        row.className = "flex items-center gap-2 p-2 bg-zinc-800 border border-zinc-700 rounded";
        row.innerHTML = `
            <span class="w-24 text-sm text-white">${name}</span>
            <button class="attr-btn minus px-2 py-1 bg-zinc-700 rounded text-white hover:bg-zinc-600" data-attr="${key}">-</button>
            <input type="number" value="${val}" min="8" max="15" class="w-12 text-center bg-zinc-900 border border-zinc-600 rounded text-white" readonly>
            <button class="attr-btn plus px-2 py-1 bg-zinc-700 rounded text-white hover:bg-zinc-600" data-attr="${key}">+</button>
            <span class="w-10 text-center text-sm text-amber-400">${mod >= 0 ? '+' : ''}${mod}</span>
        `;
        container.appendChild(row);
    }
    document.querySelectorAll(".attr-btn.minus").forEach(btn => {
        btn.addEventListener("click", () => {
            if (charAttrs[btn.dataset.attr] > 8) {
                charAttrs[btn.dataset.attr]--;
                renderAttrEditor();
                updateCharPreview();
            }
        });
    });
    document.querySelectorAll(".attr-btn.plus").forEach(btn => {
        btn.addEventListener("click", () => {
            if (charAttrs[btn.dataset.attr] < 15) {
                charAttrs[btn.dataset.attr]++;
                renderAttrEditor();
                updateCharPreview();
            }
        });
    });
    const used = calcTotalCost();
    const pointsEl = $("#attr-points");
    if (pointsEl) pointsEl.textContent = 27 - used;
    const btn = $("#btn-create");
    if (btn) btn.disabled = used > 27;
}

function updateCharPreview() {
    const name = $("#char-name")?.value || "Герой";
    const conMod = Math.floor((charAttrs.con - 10) / 2);
    const maxHp = 10 + conMod;
    const ac = 10 + Math.floor((charAttrs.dex - 10) / 2);
    const el = $("#char-preview");
    if (!el) return;
    let html = `<div class="text-amber-400 text-lg font-bold">${name}</div>`;
    const stats = [["Уровень", "1"], ["Хиты", maxHp], ["Класс доспеха", ac], ["Золото", "50"]];
    for (const [label, val] of stats) {
        html += `<div class="flex justify-between py-1 border-b border-zinc-700"><span class="text-gray-400">${label}</span><span class="text-white">${val}</span></div>`;
    }
    for (const [key, name] of Object.entries(ATTR_NAMES)) {
        const val = charAttrs[key];
        const mod = Math.floor((val - 10) / 2);
        html += `<div class="flex justify-between py-1 border-b border-zinc-700"><span class="text-gray-400">${name}</span><span class="text-white">${val} (${mod >= 0 ? '+' : ''}${mod})</span></div>`;
    }
    el.innerHTML = html;
}

async function createCharacter() {
    const name = $("#char-name")?.value || "Герой";
    try {
        await api("/api/player", "POST", { name, attributes: charAttrs });
        $("#creation-overlay").style.display = "none";
        const app = $("#main-app");
        if (app) app.style.display = "flex";
        loadWorld();
        loadPlayer();
    } catch (e) { setStatus(`Ошибка: ${e.message}`); }
}

async function checkExistingPlayer() {
    try {
        const data = await api("/api/player");
        if (data?.name && data.name !== "Герой") {
            $("#creation-overlay").style.display = "none";
            const app = $("#main-app");
            if (app) app.style.display = "flex";
            return true;
        }
    } catch (e) {}
    return false;
}
