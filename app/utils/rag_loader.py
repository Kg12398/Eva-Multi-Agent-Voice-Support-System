import os

# Force HuggingFace to use local cache only (no network calls)
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from langchain_chroma import Chroma
from sentence_transformers import SentenceTransformer
from typing import List

class SimpleEmbeddings:
    def __init__(self):
        # Must match the model used in index_knowledge.py
        # local_files_only=True prevents any HuggingFace network requests
        self.model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts).tolist()
    
    def embed_query(self, text: str) -> List[float]:
        return self.model.encode([text])[0].tolist()

def get_vector_store():
    """Retrieve the pre-indexed vector store."""
    vector_db_path = "knowledge_base/vector_store"
    
    if not os.path.exists(vector_db_path):
        print("⚠️ Warning: Vector store not found. Have you run index_knowledge.py?")
        return None
        
    embeddings = SimpleEmbeddings()
    
    vector_db = Chroma(
        persist_directory=vector_db_path,
        embedding_function=embeddings
    )
    
    return vector_db
