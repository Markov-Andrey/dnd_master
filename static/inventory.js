// inventory.js — инвентарь и экипировка

const SLOT_NAMES = {
    head: "Голова", neck: "Шея", chest: "Грудь", hands: "Руки",
    weapon: "Оружие", shield: "Щит", ring: "Кольцо", feet: "Ноги",
};
let dragData = null;

function openInventory() {
    $("#inv-overlay")?.classList.remove("hidden");
    renderInventory();
}

function closeInventory() {
    $("#inv-overlay")?.classList.add("hidden");
}

function renderInventory() {
    api("/api/inventory").then(inv => {
        renderEquipSlots(inv.equipment);
        renderBackpack(inv.backpack);
        const w = calcWeight(inv);
        const weightEl = $("#inv-weight");
        if (weightEl) weightEl.textContent = `Вес: ${w.toFixed(1)} кг`;
    });
}

function renderEquipSlots(equip) {
    document.querySelectorAll(".inv-slot").forEach(el => {
        const slot = el.dataset.slot;
        const item = equip[slot];
        el.classList.toggle("has-item", !!item);
        const icon = el.querySelector(".slot-icon");
        const label = el.querySelector(".slot-label");
        if (icon) icon.textContent = item ? item.icon : "";
        if (label) label.textContent = item ? item.name : SLOT_NAMES[slot];
        el.onmouseenter = item ? (e) => showTooltip(e, item) : () => hideTooltip();
        el.onmouseleave = () => hideTooltip();
        el.onclick = () => { if (item) unequipItem(slot); };
    });
}

function renderBackpack(bp) {
    const grid = $("#inv-grid");
    if (!grid) return;
    grid.innerHTML = "";
    bp.forEach((item) => {
        const cell = document.createElement("div");
        cell.className = `inv-cell ${item ? 'has-item' : ''} bg-zinc-800 border border-zinc-700 rounded aspect-square flex flex-col items-center justify-center cursor-pointer hover:border-amber-600`;
        if (item) {
            cell.innerHTML = `<span class="text-xl">${item.icon}</span>` +
                (item.stack_size > 1 ? `<span class="text-xs text-gray-400">×${item.stack_size}</span>` : "");
            cell.onmouseenter = (e) => showTooltip(e, item);
            cell.onmouseleave = () => hideTooltip();
            cell.onclick = () => equipItem(item.id);
        }
        grid.appendChild(cell);
    });
}

function showTooltip(e, item) {
    const tt = $("#inv-tooltip");
    if (!tt) return;
    const props = Object.entries(item.properties || {}).map(([k, v]) => `<span class="text-gray-500">${k}:</span> ${v}`).join("<br>");
    tt.innerHTML = `
        <div class="text-amber-400 font-bold">${item.icon} ${item.name}</div>
        <div class="text-xs text-gray-500 mt-1">${item.item_type}</div>
        <div class="text-xs text-gray-400 mt-1">${item.description || ""}</div>
        ${props ? `<div class="text-xs text-gray-500 mt-2">${props}</div>` : ""}`;
    tt.classList.remove("hidden");
    const r = e.currentTarget.getBoundingClientRect();
    let x = r.left + r.width / 2 - tt.offsetWidth / 2;
    let y = r.top - tt.offsetHeight - 8;
    if (y < 0) y = r.bottom + 8;
    if (x < 4) x = 4;
    tt.style.left = x + "px";
    tt.style.top = y + "px";
}

function hideTooltip() {
    $("#inv-tooltip")?.classList.add("hidden");
}

async function equipItem(itemId) {
    await api("/api/inventory/equip", "POST", { item_id: itemId });
    renderInventory();
}

async function unequipItem(slot) {
    await api("/api/inventory/unequip", "POST", { slot });
    renderInventory();
}

function calcWeight(inv) {
    let w = 0;
    for (const item of Object.values(inv.equipment || {})) {
        if (item) w += (item.properties?.weight || 1) * (item.stack_size || 1);
    }
    for (const item of inv.backpack || []) {
        if (item) w += (item.properties?.weight || 1) * (item.stack_size || 1);
    }
    return w;
}
