import os
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from typing import List
from dotenv import load_dotenv

from pharma_rag.services.embeddings import get_embedding_function

load_dotenv()

from langchain_huggingface import HuggingFaceEmbeddings

def get_embedding_function():
    try:
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    except Exception as e:
        print("Warning: HF embeddings failed. Using mock mode.", e)
        return None



class ChromaService:
    def __init__(self, collection_name: str = "pharma_docs"):
        # Use shared helper to obtain an embedding function (HF / Gemini / OpenAI)
        self.embedding_function = get_embedding_function()

        self.collection_name = collection_name

        # Initialize Chroma without embedding function if not available
        if self.embedding_function:
            self.chroma_client = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embedding_function,
                persist_directory="./chroma_data",
            )
            print("ChromaDB initialized with embedding function.")
        else:
            # Mock Chroma client for demonstration
            self.chroma_client = None
            print("ChromaDB initialized in mock mode (no embeddings).")


    def ingest_documents(self, file_paths: List[str]):
        """Loads and splits documents, then embeds and stores them in ChromaDB."""
        if not self.chroma_client:
            print("Warning: ChromaDB is in mock mode. Documents will not be stored.")
            return
        
        documents = []
        for path in file_paths:
            loader = PyPDFLoader(path)
            documents.extend(loader.load())

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        
        chunks = text_splitter.split_documents(documents)
        
        self.chroma_client.add_documents(documents=chunks)
        print(f"Successfully ingested {len(chunks)} chunks into ChromaDB.")

    def load_chunks(self, document_chunks: List[dict]):
        """Loads pre-chunked documents into ChromaDB."""
        if not self.chroma_client:
            print("Warning: ChromaDB is in mock mode. Chunks will not be stored.")
            print(f"Mock ingestion: {len(document_chunks)} chunks would be stored.")
            return
        
        # Convert dict chunks to langchain documents if needed
        from langchain_core.documents import Document
        documents = [
            Document(page_content=chunk.get("text", str(chunk)), 
                    metadata=chunk.get("metadata", {}))
            for chunk in document_chunks
        ]
        
        self.chroma_client.add_documents(documents=documents)
        print(f"Successfully ingested {len(document_chunks)} chunks into ChromaDB.")

    def semantic_search(self, query: str, k: int = 5) -> List[str]:
        """Performs a similarity search and returns relevant text content."""
        if not self.chroma_client:
            print(f"Warning: ChromaDB is in mock mode. Returning mock results for query: {query}")
            return [f"Mock result {i+1} for query: {query}" for i in range(min(k, 3))]
        
        results = self.chroma_client.similarity_search(query, k=k)
        
        return [doc.page_content for doc in results]