"""Добавить факты в RAG-память NPC.

Usage:
  python rag_add.py npc_kira "Кира любит зелья с корицей"
  python rag_add.py npc_kira "Кира боится пауков" --facts "страх,аллергия"
"""
import sys
sys.path.insert(0, ".")

from dialogue.rag_memory import RAGMemory

def main():
    if len(sys.argv) < 3:
        print("Usage: python rag_add.py <npc_id> <fact_text> [--facts 'tag1,tag2']")
        sys.exit(1)

    npc_id = sys.argv[1]
    fact = sys.argv[2]
    tags = []
    if "--facts" in sys.argv:
        idx = sys.argv.index("--facts")
        tags = [t.strip() for t in sys.argv[idx + 1].split(",")]

    rag = RAGMemory()
    rag.store(npc_id, fact, facts=tags if tags else None, meta={"type": "manual"})

    all_facts = rag.get_all(npc_id)
    print(f"Added. Total facts for {npc_id}: {len(all_facts)}")
    for f in all_facts:
        print(f"  [{f['metadata'].get('type', '?')}] {f['document']}")

if __name__ == "__main__":
    main()
