from ai.services.gemini import GeminiClient
from ai.rag.vector_store import JSONVectorStore

class RAGRetriever:
    def __init__(self):
        self.vector_store = JSONVectorStore()
        self.gemini = GeminiClient()
        
    def retrieve_context(self, query, top_k=3):
        """
        Embeds the query and searches the vector store for relevant context.
        """
        query_embedding = self.gemini.get_embeddings(query)
        if not query_embedding:
            return ""
            
        results = self.vector_store.search(query_embedding, top_k=top_k)
        
        if not results:
            return ""
            
        context_parts = []
        for r in results:
            if r["score"] > 0.6: # similarity threshold
                context_parts.append(r["text"])
                
        return "\n\n".join(context_parts)
