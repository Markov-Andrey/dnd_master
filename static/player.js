// player.js — информация об игроке

async function loadPlayer() {
    try {
        playerData = await api("/api/player");
        updatePlayerInfo();
        loadGold();
    } catch (e) {}
}

function updatePlayerInfo() {
    if (!playerData) return;
    const info = $("#player-info");
    if (info) {
        const hpPct = playerData.max_hp > 0 ? (playerData.hp / playerData.max_hp * 100) : 100;
        info.innerHTML = `
            <div class="text-amber-400 text-sm font-bold">${playerData.name}</div>
            <div class="text-xs text-gray-500 mt-1">Ур. ${playerData.level} | XP: ${playerData.xp}/${playerData.xp_to_next || '?'}</div>
            <div class="w-full h-1.5 bg-zinc-700 rounded overflow-hidden mt-1">
                <div class="h-full ${hpPct < 30 ? 'bg-red-500' : 'bg-green-500'}" style="width:${hpPct}%"></div>
            </div>
            <div class="text-xs text-gray-500">HP: ${playerData.hp}/${playerData.max_hp} | AC: ${playerData.ac || 10}</div>
        `;
    }
    const attrs = $("#player-attrs");
    if (attrs) {
        const names = { str: "СИЛ", dex: "ЛОВ", con: "ТЕЛ", int: "ИНТ", wis: "МУД", cha: "ХАР" };
        let html = "";
        for (const [k, v] of Object.entries(playerData.attributes || {})) {
            const mod = playerData.modifiers ? playerData.modifiers[k] : 0;
            html += `<div class="text-center p-1 bg-zinc-800 border border-zinc-700 rounded">
                <div class="text-xs text-gray-500">${names[k] || k}</div>
                <div class="text-lg font-bold">${v}</div>
                <div class="text-xs text-amber-400">${mod >= 0 ? '+' : ''}${mod}</div>
            </div>`;
        }
        attrs.innerHTML = html;
    }
}

async function loadGold() {
    try {
        const data = await api("/api/gold");
        const el = $("#gold-display");
        if (el) el.textContent = `💰 ${data.gold || 0}`;
    } catch (e) {}
}
