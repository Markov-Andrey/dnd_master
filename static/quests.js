// quests.js — квестовая панель

let questData = { available: [], active: [], completed: [] };

async function loadQuests() {
    try {
        questData = await api("/api/quests");
        renderQuestPanel();
        renderQuestBadge();
    } catch (e) {}
}

function renderQuestBadge() {
    const badge = $("#quest-badge");
    if (badge) {
        const count = questData.active.length;
        badge.textContent = count;
        badge.style.display = count > 0 ? "inline-block" : "none";
    }
}

function renderQuestPanel() {
    const avail = $("#quest-available");
    const active = $("#quest-active");
    const done = $("#quest-done");
    if (avail) avail.innerHTML = renderQuestList(questData.available, "available");
    if (active) active.innerHTML = renderQuestList(questData.active, "active");
    if (done) done.innerHTML = renderQuestList(questData.completed, "completed");
}

function renderQuestList(quests, mode) {
    if (!quests.length) return '<div class="quest-empty">Пусто</div>';
    return quests.map(q => {
        const objectives = (q.objectives || []).map(o => {
            const icon = o.is_complete ? "✓" : `${o.current}/${o.required}`;
            return `<div class="quest-obj ${o.is_complete ? 'done' : ''}">${icon} ${o.description}</div>`;
        }).join("");
        const rewards = [];
        if (q.rewards?.xp) rewards.push(`${q.rewards.xp} XP`);
        if (q.rewards?.gold) rewards.push(`${q.rewards.gold} 💰`);
        if (q.rewards?.items?.length) rewards.push(q.rewards.items.join(", "));
        const acceptBtn = mode === "available"
            ? `<button class="quest-accept-btn" onclick="acceptQuest('${q.id}')">Взять</button>`
            : "";
        return `<div class="quest-card ${mode}">
            <div class="quest-header">
                <span class="quest-name">${q.name}</span>
                <span class="quest-level">Ур.${q.level_required}</span>
            </div>
            <div class="quest-desc">${q.description}</div>
            <div class="quest-objectives">${objectives}</div>
            ${rewards.length ? `<div class="quest-rewards">Награда: ${rewards.join(" | ")}</div>` : ""}
            ${acceptBtn}
        </div>`;
    }).join("");
}

async function acceptQuest(questId) {
    try {
        const res = await api("/api/quests/accept", "POST", { quest_id: questId });
        if (res.success) {
            addMessage(res.message, "system");
            await loadQuests();
        } else {
            addMessage(res.message, "system");
        }
    } catch (e) { setStatus(`Ошибка: ${e.message}`); }
}

function toggleQuests() {
    const overlay = $("#quest-overlay");
    if (!overlay) return;
    const isHidden = overlay.classList.contains("hidden");
    if (isHidden) {
        loadQuests();
        overlay.classList.remove("hidden");
    } else {
        overlay.classList.add("hidden");
    }
}

function showQuestNotification(updates) {
    if (!updates?.length) return;
    const box = $("#quest-notifications");
    if (!box) return;
    for (const u of updates) {
        const el = document.createElement("div");
        el.className = "quest-notify";
        if (u.complete && u.rewards) {
            el.innerHTML = `<span class="qn-title">🏆 Квест выполнен: ${u.quest}</span>
                <span class="qn-reward">+${u.rewards.xp || 0} XP, +${u.rewards.gold || 0} золота</span>`;
        } else {
            el.innerHTML = `<span class="qn-title">📋 ${u.quest}</span>
                <span class="qn-progress">${u.objective}: ${u.progress}</span>`;
        }
        box.appendChild(el);
        setTimeout(() => el.remove(), 4000);
    }
}
