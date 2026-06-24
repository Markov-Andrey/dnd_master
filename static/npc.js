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

    fillDialogueSidebar(npc);
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

function fillDialogueSidebar(npc) {
    const sb = $("#dialogue-sidebar");
    if (!sb || !npc) return;

    const f = npc.relationships?.friendship || 0;
    const l = npc.relationships?.love || 0;
    const rl = npc.relation_level || "незнакомец";
    const ll = npc.love_level || "нет";
    const mood = npc.mood || "спокоен";
    const traits = npc.personality?.traits?.join(", ") || "";
    const core = npc.personality?.core || "";
    const moodColors = { спокоен: "#6a9", рад: "#da4", грустный: "#68a", злой: "#c44", испуганный: "#c84", влюблён: "#e6a" };

    let html = "";

    if (npc.portrait) {
        html += `<img src="/static/portraits/${npc.portrait}" class="ds-portrait" alt="${npc.name}">`;
    }
    html += `<div class="ds-name">${npc.name || npc.id}</div>`;
    if (traits) html += `<div class="ds-traits">${traits}</div>`;
    html += `<div class="ds-mood"><span class="ds-mood-dot" style="background:${moodColors[mood] || '#888'}"></span>${mood}</div>`;

    html += `<hr class="ds-divider">`;

    const fPct = ((f + 100) / 2).toFixed(0);
    const lPct = ((l + 100) / 2).toFixed(0);
    html += `<div class="ds-section">
        <div class="ds-label">Отношения</div>
        <div class="rel-row"><span class="rel-label">Дружба</span><div class="rel-bar"><div class="rel-bar-center"></div><div class="rel-fill ${f>=0?'positive':'negative'}" style="left:${f>=0?'50%':fPct+'%'};right:${f>=0?(100-fPct)+'%':'50%'}"></div></div><span class="rel-val">${f>0?'+':''}${f}</span><span class="rel-level">${rl}</span></div>
        <div class="rel-row"><span class="rel-label">Любовь</span><div class="rel-bar"><div class="rel-bar-center"></div><div class="rel-fill ${l>=0?'positive':'negative'}" style="left:${l>=0?'50%':lPct+'%'};right:${l>=0?(100-lPct)+'%':'50%'}"></div></div><span class="rel-val">${l>0?'+':''}${l}</span><span class="rel-level">${ll}</span></div>
    </div>`;

    if (core) {
        html += `<hr class="ds-divider"><div class="ds-section"><div class="ds-label">Суть</div><div class="ds-text">${core}</div></div>`;
    }

    if (npc.background) {
        html += `<div class="ds-section"><div class="ds-label">Предыстория</div><div class="ds-text">${npc.background}</div></div>`;
    }

    if (npc.lore) {
        html += `<div class="ds-section"><div class="ds-label">Лор</div><div class="ds-text">${npc.lore}</div></div>`;
    }

    const prefs = npc.preferences || {};
    const likes = prefs.likes?.join(", ");
    const dislikes = prefs.dislikes?.join(", ");
    const fears = prefs.fears?.join(", ");
    if (likes || dislikes || fears) {
        html += `<div class="ds-section"><div class="ds-label">Предпочтения</div><div class="ds-text">`;
        if (likes) html += `+ ${likes}<br>`;
        if (dislikes) html += `- ${dislikes}<br>`;
        if (fears) html += `! ${fears}`;
        html += `</div></div>`;
    }

    const rels = npc.relations || {};
    const relEntries = Object.entries(rels);
    if (relEntries.length) {
        html += `<div class="ds-section"><div class="ds-label">Знакомые</div>`;
        for (const [rid, rtype] of relEntries) {
            html += `<div class="ds-text">● ${rtype} — ${rid.replace("npc_", "")}</div>`;
        }
        html += `</div>`;
    }

    const quests = npc.quest_hooks || [];
    if (quests.length) {
        html += `<div class="ds-section"><div class="ds-label">Квесты</div>`;
        for (const q of quests) {
            const text = q.text || q;
            const done = q.status === "completed";
            html += `<div class="ds-quest ${done ? 'ds-quest-done' : 'ds-quest-active'}">${done ? '✓ ' : '● '}${text}</div>`;
        }
        html += `</div>`;
    }

    const mems = npc.memories || [];
    if (mems.length) {
        html += `<div class="ds-section"><div class="ds-label">Воспоминания (${mems.length})</div>`;
        for (const m of mems.slice(-5)) {
            html += `<div class="ds-mem">[${m.category}] ${m.text}</div>`;
        }
        html += `</div>`;
    }

    if (npc.current_summary) {
        html += `<div class="ds-section"><div class="ds-label">Саммари</div><div class="ds-summary">${npc.current_summary}</div></div>`;
    }

    html += `<div class="ds-section"><div class="ds-label">Имя</div><div class="ds-text">${npc.name_known ? npc.name + ' (известно)' : 'Неизвестно игроку'}</div></div>`;

    sb.innerHTML = html;
}

function closeDialogue() {
    const panel = $("#dialogue-panel");
    if (panel) panel.style.display = "none";
    const sb = $("#dialogue-sidebar");
    if (sb) sb.innerHTML = "";
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
        if (res.quest_updates?.length) showQuestNotification(res.quest_updates);
        loadQuests();
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
            addMessage(`[${sc.skill_name} ${sc.total} vs DC ${sc.dc} — ${sc.success ? "УСПЕХ" : "ПРОВАЛ"}]`, "check");
        }
        if (res.item_result) {
            const ir = res.item_result;
            addMessage(`Предмет ${ir.accepted ? "принят" : "отвергнут"}: ${ir.reason}`, "system");
        }
        if (res.state) {
            fillDialogueSidebar(res.state);
            updateNpcDebugPanel(res.state);
        }
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
