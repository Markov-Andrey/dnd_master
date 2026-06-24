// shop.js — магазин, сундуки, лут

async function openShop(shopType = "general") {
    try {
        const data = await api(`/api/shop/${shopType}`);
        const gold = await api("/api/gold");
        const titleEl = $("#shop-title");
        const goldEl = $("#shop-gold");
        if (titleEl) titleEl.textContent = data.name;
        if (goldEl) goldEl.textContent = `💰 ${gold.gold || 0}`;
        const items = $("#shop-items");
        if (items) {
            items.innerHTML = "";
            for (const item of data.inventory) {
                const div = document.createElement("div");
                div.className = "shop-item flex items-center gap-2 p-2 bg-zinc-800 border border-zinc-700 rounded cursor-pointer hover:border-amber-600 mb-2";
                div.innerHTML = `
                    <span class="text-xl">${item.icon}</span>
                    <div class="flex-1">
                        <div class="text-sm text-white">${item.name}</div>
                        <div class="text-xs text-amber-400">💰 ${item.sell_price}</div>
                    </div>
                `;
                div.addEventListener("click", () => buyItem(shopType, item.item_id));
                items.appendChild(div);
            }
        }
        $("#shop-overlay")?.classList.remove("hidden");
    } catch (e) { setStatus(`Ошибка: ${e.message}`); }
}

async function buyItem(shopType, itemId) {
    try {
        const data = await api("/api/shop/buy", "POST", { shop_type: shopType, item_id: itemId });
        setStatus(data.message);
        if (data.success) {
            const gold = await api("/api/gold");
            const goldEl = $("#shop-gold");
            if (goldEl) goldEl.textContent = `💰 ${gold.gold || 0}`;
        }
    } catch (e) { setStatus(`Ошибка: ${e.message}`); }
}

function closeShop() {
    $("#shop-overlay")?.classList.add("hidden");
    loadGold();
}

async function openChest() {
    try {
        const data = await api("/api/chest/open", "POST", { type: "wooden" });
        showLoot(data.loot);
    } catch (e) { setStatus(`Ошибка: ${e.message}`); }
}

function showLoot(loot) {
    const body = $("#loot-body");
    if (!body) return;
    body.innerHTML = "";
    for (const item of loot) {
        const div = document.createElement("div");
        div.className = "flex items-center gap-2 p-2 bg-zinc-800 border border-zinc-700 rounded mb-2";
        if (item.gold) {
            div.innerHTML = `<span class="text-xl">${item.icon || '💰'}</span> <span class="text-sm">${item.amount || 1} ${item.name || 'Золото'} (+${item.gold} 💰)</span>`;
        } else {
            div.innerHTML = `<span class="text-xl">${item.icon || '?'}</span> <span class="text-sm">${item.name || item.item_id} (${item.rarity || 'common'})</span>`;
        }
        body.appendChild(div);
    }
    $("#loot-overlay")?.classList.remove("hidden");
    loadGold();
    loadPlayer();
}

function closeLoot() {
    $("#loot-overlay")?.classList.add("hidden");
}
