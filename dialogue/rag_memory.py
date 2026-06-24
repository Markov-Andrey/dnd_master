"""RAG-память на ChromaDB: хранение саммари, поиск по NPC."""
import chromadb
from chromadb.config import Settings
from core.config import CHROMA_DB_DIR, CHROMA_COLLECTION, RAG_TOP_K


class RAGMemory:
    def __init__(self):
        self.col = chromadb.PersistentClient(
            path=CHROMA_DB_DIR, settings=Settings(anonymized_telemetry=False)
        ).get_or_create_collection(CHROMA_COLLECTION)

    def store(self, npc_id, summary, facts=None, meta=None):
        md = {"npc_id": npc_id}
        if facts: md["facts"] = ", ".join(facts)
        if meta: md.update(meta)
        self.col.add(documents=[summary], ids=[f"{npc_id}_{self.col.count()}"], metadatas=[md])

    def query(self, npc_id, query_text, top_k=RAG_TOP_K):
        return self.col.query(query_texts=[query_text], n_results=top_k, where={"npc_id": npc_id}).get("documents", [[]])[0]

    def get_all(self, npc_id):
        r = self.col.get(where={"npc_id": npc_id})
        return [{"id": i, "document": d, "metadata": m}
                for d, m, i in zip(r.get("documents", []), r.get("metadatas", []), r.get("ids", []))]
