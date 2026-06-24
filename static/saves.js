// saves.js — сохранения и загрузка

function openSaves() {
    $("#saves-overlay")?.classList.remove("hidden");
    loadSavesList();
}

function closeSaves() {
    $("#saves-overlay")?.classList.add("hidden");
}

async function loadSavesList() {
    try {
        const saves = await api("/api/save/list");
        const container = $("#saves-list");
        if (!container) return;
        if (!saves.length) {
            container.innerHTML = '<div class="text-gray-500 text-center py-4">Нет сохранений</div>';
            return;
        }
        container.innerHTML = "";
        for (const save of saves) {
            const div = document.createElement("div");
            div.className = "flex items-center gap-2 p-3 bg-zinc-800 border border-zinc-700 rounded cursor-pointer hover:border-amber-600 mb-2";
            div.innerHTML = `
                <div class="flex-1">
                    <div class="text-amber-400 text-sm font-bold">${save.name}</div>
                    <div class="text-xs text-gray-500">${save.player_name} (ур. ${save.player_level}) | ${save.saved_at?.slice(0, 16) || '?'}</div>
                </div>
                <button class="save-delete text-gray-500 hover:text-red-500" data-name="${save.name}">🗑</button>
            `;
            div.addEventListener("click", (e) => {
                if (!e.target.classList.contains("save-delete")) loadSave(save.name);
            });
            div.querySelector(".save-delete")?.addEventListener("click", (e) => {
                e.stopPropagation();
                deleteSave(save.name);
            });
            container.appendChild(div);
        }
    } catch (e) {}
}

async function quickSave() {
    try {
        await api("/api/save/quick", "POST");
        setStatus("Сохранено!");
    } catch (e) { setStatus("Ошибка сохранения"); }
}

async function loadSave(name) {
    try {
        await api("/api/load", "POST", { name });
        closeSaves();
        loadWorld();
        loadPlayer();
        setStatus("Загружено!");
    } catch (e) { setStatus("Ошибка загрузки"); }
}

async function deleteSave(name) {
    try {
        await api("/api/save/delete", "POST", { name });
        loadSavesList();
    } catch (e) {}
}
