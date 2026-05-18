import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from sentence_transformers import SentenceTransformer
from typing import List

class SimpleEmbeddings:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts).tolist()
    
    def embed_query(self, text: str) -> List[float]:
        return self.model.encode([text])[0].tolist()

def index_docs():
    print("Starting Knowledge Base Indexing...")
    
    # 1. Load Documents (Text and PDF)
    docs_path = "knowledge_base/documents"
    if not os.path.exists(docs_path):
        os.makedirs(docs_path)
        
    # We load everything in the documents folder
    txt_loader = DirectoryLoader(docs_path, glob="**/*.txt", loader_cls=TextLoader)
    pdf_loader = DirectoryLoader(docs_path, glob="**/*.pdf", loader_cls=PyPDFLoader)
    
    documents = txt_loader.load() + pdf_loader.load()
    print(f"Loaded {len(documents)} source documents.")

    # 2. Split Text (chunking)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_documents(documents)
    print(f"Split into {len(chunks)} knowledge chunks.")

    # 3. Create Embeddings & Store in Vector DB
    embeddings = SimpleEmbeddings()

    vector_db_path = "knowledge_base/vector_store"
    
    # Create the vector store
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=vector_db_path
    )
    
    print(f"Knowledge Base ready! Saved to: {vector_db_path}")

if __name__ == "__main__":
    index_docs()
