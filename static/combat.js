// combat.js — боевая система

async function startCombat() {
    setStatus("Поиск врагов...");
    try {
        const data = await api("/api/combat/start", "POST");
        if (data.error) { setStatus(data.error); return; }
        if (data.message && !data.state) { setStatus(data.message); return; }
        inCombat = true;
        $("#combat-overlay")?.classList.remove("hidden");
        renderCombatState(data.state);
        setStatus("Бой начался!");
    } catch (e) { setStatus(`Ошибка: ${e.message}`); }
}

function renderCombatState(state) {
    if (!state) return;
    const roundEl = $("#combat-round");
    if (roundEl) roundEl.textContent = `Раунд ${state.round}`;
    const container = $("#combat-combatants");
    if (container) {
        container.innerHTML = "";
        for (const c of state.combatants) {
            const div = document.createElement("div");
            const hpPct = c.max_hp > 0 ? (c.hp / c.max_hp * 100) : 0;
            div.className = `combatant-card ${c.is_player ? 'is-player' : 'is-enemy'} ${!c.is_alive ? 'dead' : ''} p-3 bg-zinc-800 border rounded mb-2 flex items-center gap-3`;
            div.style.borderColor = c.is_player ? '#d4af37' : '#c0392b';
            div.innerHTML = `
                <span class="font-bold flex-1">${c.is_player ? '🎮 ' : '💀 '}${c.name}</span>
                <div class="hp-bar w-20 h-1.5 bg-zinc-700 rounded overflow-hidden"><div class="h-full ${hpPct < 30 ? 'bg-red-500' : 'bg-green-500'}" style="width:${hpPct}%"></div></div>
                <span class="text-xs text-gray-400">${c.hp}/${c.max_hp}</span>
            `;
            container.appendChild(div);
        }
    }
    const log = $("#combat-log");
    if (log) {
        log.innerHTML = "";
        for (const entry of (state.log || [])) {
            if (entry.type === "attack" && entry.message) {
                log.innerHTML += entry.message + "\n";
            } else if (entry.type === "system") {
                log.innerHTML += `<span class="text-amber-400">${entry.message || ''}</span>\n`;
            }
        }
        log.scrollTop = log.scrollHeight;
    }
    const isPlayerTurn = state.combatants.some(c => c.is_player && c.is_alive);
    const hasEnemies = state.combatants.some(c => !c.is_player && c.is_alive);
    ["btn-attack", "btn-defend", "btn-potion", "btn-flee"].forEach(id => {
        const btn = $(`#${id}`);
        if (btn) btn.disabled = !isPlayerTurn || (id === "btn-attack" && !hasEnemies);
    });
    if (!state.is_active) {
        const result = $("#combat-result");
        if (result) {
            result.textContent = state.winner_team === 0 ? "🏆 Победа!" : "💀 Поражение...";
            result.classList.remove("hidden");
        }
        ["btn-attack", "btn-defend", "btn-potion", "btn-flee"].forEach(id => {
            const btn = $(`#${id}`);
            if (btn) btn.disabled = true;
        });
    }
}

async function combatAttack() {
    try {
        const data = await api("/api/combat/attack", "POST", { target: 0, attack: 0 });
        renderCombatState(data.state);
        if (data.loot?.length) showLoot(data.loot);
    } catch (e) { setStatus(`Ошибка: ${e.message}`); }
}

async function combatDefend() {
    try {
        const data = await api("/api/combat/defend", "POST");
        renderCombatState(data.state);
    } catch (e) {}
}

async function combatPotion() {
    try {
        const data = await api("/api/combat/use_potion", "POST");
        if (data.error) { setStatus(data.error); return; }
        renderCombatState(data.state);
    } catch (e) {}
}

async function combatFlee() {
    try {
        const data = await api("/api/combat/flee", "POST");
        renderCombatState(data.state);
        if (data.message === "Вы сбежали!") setTimeout(closeCombat, 1000);
    } catch (e) {}
}

function closeCombat() {
    inCombat = false;
    $("#combat-overlay")?.classList.add("hidden");
    $("#combat-result")?.classList.add("hidden");
    loadPlayer();
    loadGold();
}
