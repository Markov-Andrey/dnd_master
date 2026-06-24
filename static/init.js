// init.js — инициализация и привязка событий

function bindEvents() {
    // Диалог
    $("#btn-close-dialogue")?.addEventListener("click", closeDialogue);
    $("#btn-end-dialogue")?.addEventListener("click", endDialogue);
    $("#btn-send")?.addEventListener("click", sendMessage);
    $("#player-input")?.addEventListener("keydown", (e) => { if (e.key === "Enter") sendMessage(); });

    // Бой
    $("#btn-combat")?.addEventListener("click", startCombat);
    $("#btn-attack")?.addEventListener("click", combatAttack);
    $("#btn-defend")?.addEventListener("click", combatDefend);
    $("#btn-potion")?.addEventListener("click", combatPotion);
    $("#btn-flee")?.addEventListener("click", combatFlee);
    $("#btn-combat-close")?.addEventListener("click", closeCombat);

    // Отдых
    $("#btn-rest-short")?.addEventListener("click", shortRest);
    $("#btn-rest-long")?.addEventListener("click", longRest);

    // Магазин
    $("#btn-shop")?.addEventListener("click", () => openShop("general"));
    $("#btn-shop-close")?.addEventListener("click", closeShop);

    // Сундуки
    $("#btn-chest")?.addEventListener("click", openChest);
    $("#btn-loot-close")?.addEventListener("click", closeLoot);

    // Инвентарь
    $("#btn-inv")?.addEventListener("click", openInventory);
    $("#inv-close")?.addEventListener("click", closeInventory);
    $("#inv-overlay")?.addEventListener("click", (e) => { if (e.target === e.currentTarget) closeInventory(); });

    // Сохранения
    $("#btn-save")?.addEventListener("click", quickSave);
    $("#btn-load")?.addEventListener("click", openSaves);
    $("#btn-saves-close")?.addEventListener("click", closeSaves);

    // Квесты
    $("#quest-overlay")?.addEventListener("click", (e) => { if (e.target === e.currentTarget) toggleQuests(); });

    // Создание персонажа
    $("#char-name")?.addEventListener("input", updateCharPreview);
    $("#btn-create")?.addEventListener("click", createCharacter);
}

async function init() {
    bindEvents();
    const hasPlayer = await checkExistingPlayer();
    if (!hasPlayer) {
        renderAttrEditor();
        updateCharPreview();
    }
    loadQuests();
}

init();
