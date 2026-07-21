from ai.services.gemini import GeminiClient
from ai.rag.vector_store import JSONVectorStore
import uuid

def ingest_text(text, source_name="General"):
    """
    Chunks a text document, generates embeddings, and saves to the vector store.
    """
    gemini = GeminiClient()
    vector_store = JSONVectorStore()
    
    # Simple chunking by paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    count = 0
    for p in paragraphs:
        if len(p) < 20: continue # skip very small chunks
        
        embedding = gemini.get_embeddings(p)
        if embedding:
            doc_id = str(uuid.uuid4())
            vector_store.add_document(doc_id, p, embedding, metadata={"source": source_name})
            count += 1
            
    print(f"Ingested {count} chunks from {source_name}")

if __name__ == "__main__":
    # Example initialization with some basic medical knowledge
    sample_knowledge = """
    A fever is a temporary increase in your body temperature, often due to an illness. 
    For adults, a fever may be uncomfortable, but usually isn't a cause for concern unless it reaches 103 F (39.4 C) or higher.
    
    Common symptoms of COVID-19 include fever, dry cough, and fatigue. Other symptoms that may affect some patients include loss of taste or smell, nasal congestion, conjunctivitis (also known as red eyes), sore throat, headache, muscle or joint pain.
    
    Acetaminophen (Tylenol) and ibuprofen (Advil, Motrin IB, others) can help lower a fever.
    """
    ingest_text(sample_knowledge, "General Guidance")
