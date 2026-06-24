// npc.js — NPC, диалоги, портреты, отношения

async function loadLocationNpcs() {
    const container = $("#location-npcs");
    if (!container) return;
    container.innerHTML = "";
    if (!currentLocation?.npc_ids?.length) {
        container.innerHTML = '<div class="text-gray-500 text-xs">Нет NPC</div>';
        return;
    }
    const npcs = await api("/api/npcs");
    const locNpcs = npcs.filter(n => currentLocation.npc_ids.includes(n.id));
    for (const npc of locNpcs) {
        container.appendChild(buildNpcCard(npc));
    }
}

function buildNpcCard(npc) {
    const card = document.createElement("div");
    card.className = "npc-card";
    const portrait = npc.portrait
        ? `<img src="/static/portraits/${npc.portrait}" class="npc-portrait" alt="${npc.name}">`
        : `<div class="npc-portrait npc-portrait-placeholder">${(npc.name || "?")[0]}</div>`;
    card.innerHTML = `
        ${portrait}
        <div class="npc-card-info">
            <div class="npc-name">${npc.name || npc.id}</div>
            <div class="npc-desc">${npc.personality?.traits?.join(", ") || npc.personality?.core || ""}</div>
            <div class="npc-relation">${npc.relation_level || "незнакомец"}</div>
        </div>
    `;
    card.addEventListener("click", () => startDialogue(npc.id));
    return card;
}

function showNpcFromArea(npcId) {
    const container = $("#location-npcs");
    if (!container) return;
    api("/api/npcs").then(npcs => {
        const npc = npcs.find(n => n.id === npcId);
        if (!npc) return;
        container.innerHTML = "";
        container.appendChild(buildNpcCard(npc));
        const locTitle = $("#loc-title");
        if (locTitle) locTitle.textContent = npc.name || "NPC";
    });
}

async function startDialogue(npcId) {
    currentNpcId = npcId;
    inDialogue = false;
    const panel = $("#dialogue-panel");
    if (panel) panel.style.display = "flex";
    const msgs = $("#messages");
    if (msgs) msgs.innerHTML = "";

    const npcs = await api("/api/npcs");
    const npc = npcs.find(n => n.id === npcId);
    const nameEl = $("#dialogue-npc-name");
    if (nameEl) nameEl.textContent = npc?.name || npcId;

    if (npc?.portrait) {
        const portraitBar = $("#dialogue-portrait");
        if (portraitBar) {
            portraitBar.innerHTML = `<img src="/static/portraits/${npc.portrait}" class="dialogue-portrait" alt="">`;
            portraitBar.style.display = "block";
        }
    }

    updateNpcDebugPanel(npc);
    setStatus("Начинаю диалог...");
    try {
        const res = await api(`/api/npc/${npcId}/start`, "POST");
        addMessage(res.npc_response, "npc");
        inDialogue = true;
        if ($("#player-input")) $("#player-input").disabled = false;
        if ($("#btn-send")) $("#btn-send").disabled = false;
        if ($("#btn-end-dialogue")) $("#btn-end-dialogue").style.display = "inline-block";
        setStatus("Диалог активен");
    } catch (e) {
        addMessage(`Ошибка: ${e.message}`, "system");
        setStatus("Ошибка при старте диалога");
    }
}

function closeDialogue() {
    const panel = $("#dialogue-panel");
    if (panel) panel.style.display = "none";
    const portraitBar = $("#dialogue-portrait");
    if (portraitBar) { portraitBar.innerHTML = ""; portraitBar.style.display = "none"; }
    currentNpcId = null;
    inDialogue = false;
    const msgs = $("#messages");
    if (msgs) msgs.innerHTML = "";
    if ($("#player-input")) $("#player-input").disabled = true;
    if ($("#btn-send")) $("#btn-send").disabled = true;
    if ($("#btn-end-dialogue")) $("#btn-end-dialogue").style.display = "none";
    setStatus("Готов");
}

async function endDialogue() {
    if (!currentNpcId) return;
    try {
        const res = await api(`/api/npc/${currentNpcId}/end`, "POST");
        addMessage("Диалог завершён. " + (res.summary?.summary || ""), "system");
        closeDialogue();
    } catch (e) {
        addMessage(`Ошибка: ${e.message}`, "system");
    }
}

async function sendMessage() {
    const input = $("#player-input");
    const msg = input?.value.trim();
    if (!msg || !currentNpcId) return;
    addMessage(msg, "player");
    input.value = "";
    setStatus("NPC думает...");
    try {
        const res = await api(`/api/npc/${currentNpcId}/say`, "POST", { message: msg });
        addMessage(res.npc_response, "npc");
        if (res.skill_check) {
            const sc = res.skill_check;
            const cls = sc.success ? "success" : "fail";
            addMessage(`[${sc.skill_name} ${sc.total} vs DC ${sc.dc} — ${sc.success ? "УСПЕХ" : "ПРОВАЛ"}]`, "check");
        }
        if (res.item_result) {
            const ir = res.item_result;
            addMessage(`Предмет ${ir.accepted ? "принят" : "отвергнут"}: ${ir.reason}`, "system");
        }
        updateNpcDebugPanel(res.state);
        setStatus("Диалог активен");
    } catch (e) {
        addMessage(`Ошибка: ${e.message}`, "system");
    }
}

function updateNpcDebugPanel(npc) {
    if (!npc) return;
    const box = $("#nearby-npcs");
    if (!box) return;
    const f = npc.relationships?.friendship || 0;
    const l = npc.relationships?.love || 0;
    const rl = npc.relation_level || "незнакомец";
    const ll = npc.love_level || "нет";
    const mood = npc.mood || "спокоен";
    const traits = npc.personality?.traits?.join(", ") || "";

    const fPct = Math.max(0, Math.min(100, (f + 100) / 2));
    const lPct = Math.max(0, Math.min(100, (l + 100) / 2));

    box.innerHTML = `
        <div style="margin-bottom:8px">
            <div style="color:#d4af37;font-weight:bold;font-size:13px">${npc.name || npc.id}</div>
            <div style="color:#666;font-size:11px;margin-top:2px">${traits}</div>
            <div style="color:#888;font-size:11px">Настроение: ${mood}</div>
        </div>
        <div class="rel-row">
            <span class="rel-label">Дружба</span>
            <div class="rel-bar">
                <div class="rel-bar-center"></div>
                <div class="rel-fill ${f >= 0 ? 'positive' : 'negative'}" style="left:${f >= 0 ? '50%' : fPct+'%'};right:${f >= 0 ? (100-fPct)+'%' : '50%'}"></div>
            </div>
            <span class="rel-val">${f > 0 ? '+' : ''}${f}</span>
            <span class="rel-level">${rl}</span>
        </div>
        <div class="rel-row">
            <span class="rel-label">Любовь</span>
            <div class="rel-bar">
                <div class="rel-bar-center"></div>
                <div class="rel-fill ${l >= 0 ? 'positive' : 'negative'}" style="left:${l >= 0 ? '50%' : lPct+'%'};right:${l >= 0 ? (100-lPct)+'%' : '50%'}"></div>
            </div>
            <span class="rel-val">${l > 0 ? '+' : ''}${l}</span>
            <span class="rel-level">${ll}</span>
        </div>
    `;
}
