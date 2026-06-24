// world.js — карта, время, перемещение

let mapMode = "global";

async function loadWorld() {
    try {
        const data = await api("/api/world");
        currentLocation = data.current_location;
        $("#location-name").textContent = currentLocation?.name || "??";
        $("#location-desc").textContent = currentLocation?.description || "";
        renderSvgMap(data);
        updateMoveButtons();
        loadLocationNpcs();
        updateLocationButtons();
        loadTime();
    } catch (e) {
        setStatus("Ошибка загрузки мира");
    }
}

function renderSvgMap(data) {
    const container = $("#svg-map");
    if (mapMode === "local" && data.svg_local) {
        container.innerHTML = data.svg_local;
    } else {
        container.innerHTML = data.svg_global || "";
    }
    attachMapListeners();
}

function attachMapListeners() {
    document.querySelectorAll(".map-tile").forEach(tile => {
        tile.addEventListener("click", () => {
            const locId = tile.dataset.loc;
            if (locId && locId !== currentLocation?.id) {
                const dir = findDirectionTo(locId);
                if (dir) movePlayer(dir);
            }
        });
    });
    document.querySelectorAll(".local-area.has-npc").forEach(area => {
        area.addEventListener("click", () => {
            const npcId = area.dataset.npc;
            if (npcId) showNpcFromArea(npcId);
        });
        area.style.cursor = "pointer";
    });
}

function findDirectionTo(targetId) {
    if (!currentLocation?.exits) return null;
    for (const [dir, id] of Object.entries(currentLocation.exits)) {
        if (id === targetId) return dir;
    }
    return null;
}

function switchMapMode(mode) {
    mapMode = mode;
    document.querySelectorAll(".map-tab").forEach(t => {
        t.classList.toggle("active", t.dataset.mode === mode);
    });
    loadWorld();
}

async function loadTime() {
    try {
        const data = await api("/api/time");
        $("#time-display").textContent = `${data.time_name}, ${data.hour}:${String(data.minute).padStart(2, '0')}`;
        $("#weather-display").textContent = data.weather_name;
        $("#day-display").textContent = `День ${data.day}`;
    } catch (e) {}
}

function updateMoveButtons() {
    const exits = currentLocation?.exits || {};
    document.querySelectorAll(".btn-move").forEach(btn => {
        btn.disabled = !exits[btn.dataset.dir];
    });
}

function updateLocationButtons() {
    const locId = currentLocation?.id;
    const hasEnc = ["forest", "cave", "ruins", "swamp", "mountain", "crossroads"].includes(locId);
    const hasShop = ["village"].includes(locId);
    const hasChest = ["cave", "ruins"].includes(locId);
    if ($("#btn-combat")) $("#btn-combat").style.display = hasEnc ? "block" : "none";
    if ($("#btn-shop")) $("#btn-shop").style.display = hasShop ? "block" : "none";
    if ($("#btn-chest")) $("#btn-chest").style.display = hasChest ? "block" : "none";
}

async function movePlayer(direction) {
    setStatus("Перемещение...");
    try {
        const data = await api("/api/world/move", "POST", { direction });
        currentLocation = data.location;
        $("#location-name").textContent = currentLocation.name;
        $("#location-desc").textContent = currentLocation.description;
        renderSvgMap(data);
        updateMoveButtons();
        loadLocationNpcs();
        updateLocationButtons();
        await api("/api/time/advance", "POST", { minutes: 30 });
        loadTime();
        if (data.random_encounter) {
            setStatus("Вы столкнулись с врагами!");
            setTimeout(() => startCombat(), 500);
        } else {
            setStatus(`Вы в: ${currentLocation.name}`);
        }
    } catch (e) {
        setStatus("Нельзя идти в этом направлении");
    }
}

async function shortRest() {
    try {
        const data = await api("/api/rest", "POST", { type: "short" });
        setStatus(data.message);
        loadPlayer();
    } catch (e) { setStatus(`Ошибка: ${e.message}`); }
}

async function longRest() {
    try {
        const data = await api("/api/rest", "POST", { type: "long" });
        setStatus(data.message);
        loadPlayer();
    } catch (e) { setStatus(`Ошибка: ${e.message}`); }
}

document.querySelectorAll(".btn-move").forEach(btn => {
    btn.addEventListener("click", () => movePlayer(btn.dataset.dir));
});
