"""Управление связями NPC.

Usage:
  python npc_relations.py npc_kira                          # показать связи
  python npc_relations.py npc_kira set npc_blacksmith муж    # установить связь
  python npc_relations.py npc_kira remove npc_blacksmith     # удалить связь
"""
import sys, json, os
sys.path.insert(0, ".")

NPC_DIR = os.path.join("db", "npcs")


def load_npc(npc_id):
    path = os.path.join(NPC_DIR, f"{npc_id}.json")
    if not os.path.exists(path):
        print(f"NPC not found: {npc_id}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def save_npc(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    npc_id = sys.argv[1]
    data, path = load_npc(npc_id)
    rels = data.get("relations", {})

    if len(sys.argv) == 2:
        if not rels:
            print(f"{npc_id}: нет связей")
        else:
            print(f"{npc_id} ({data.get('name', '?')}):")
            for rid, rtype in rels.items():
                print(f"  {rid} — {rtype}")
        return

    action = sys.argv[2]
    if action == "set" and len(sys.argv) >= 5:
        target = sys.argv[3]
        rel_type = " ".join(sys.argv[4:])
        rels[target] = rel_type
        data["relations"] = rels
        save_npc(data, path)
        print(f"OK: {npc_id} -> {target} = {rel_type}")
    elif action == "remove" and len(sys.argv) >= 4:
        target = sys.argv[3]
        if target in rels:
            del rels[target]
            data["relations"] = rels
            save_npc(data, path)
            print(f"OK: removed {target}")
        else:
            print(f"Связь {target} не найдена")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
