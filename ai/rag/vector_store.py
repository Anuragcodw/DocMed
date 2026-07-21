import os
import json
import numpy as np

class BaseVectorStore:
    def add_document(self, doc_id, text, embedding):
        raise NotImplementedError

    def search(self, query_embedding, top_k=3):
        raise NotImplementedError

class JSONVectorStore(BaseVectorStore):
    def __init__(self, index_path="vector_index.json"):
        # Put index in ai/rag directory
        self.index_path = os.path.join(os.path.dirname(__file__), index_path)
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"documents": []}

    def _save(self):
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f)

    def add_document(self, doc_id, text, embedding, metadata=None):
        self.data["documents"].append({
            "id": doc_id,
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {}
        })
        self._save()

    def search(self, query_embedding, top_k=3):
        if not self.data["documents"] or not query_embedding:
            return []
            
        q_vec = np.array(query_embedding)
        results = []
        for doc in self.data["documents"]:
            d_vec = np.array(doc["embedding"])
            # Cosine similarity
            dot_product = np.dot(q_vec, d_vec)
            norm_q = np.linalg.norm(q_vec)
            norm_d = np.linalg.norm(d_vec)
            
            if norm_q == 0 or norm_d == 0:
                sim = 0
            else:
                sim = dot_product / (norm_q * norm_d)
                
            results.append({
                "id": doc["id"],
                "text": doc["text"],
                "score": float(sim),
                "metadata": doc.get("metadata", {})
            })
            
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
