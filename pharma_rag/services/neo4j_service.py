import os
import traceback  # <-- 1. ADD THIS IMPORT AT THE TOP
from dotenv import load_dotenv
from neo4j import GraphDatabase
from typing import Callable, List, Tuple
from pharma_rag.services.embeddings import get_embedding_function
from pharma_rag.services.gemini_service import GeminiLLM, GeminiUnavailable

load_dotenv()


class Neo4jGraphRAG:
    """
    Minimal Neo4j integration without LangChain.

    Provides a Text->Cypher flow using GeminiLLM (if available) and executes
    queries with the neo4j driver. Also exposes a simple substring-based
    semantic retriever as a fallback when no vector index exists.
    """

    def __init__(self, uri: str, user: str, password: str, database: str, llm_model_name: str, embedding_model_name: str):
        self.graph_url = uri
        self.graph_username = user
        self.graph_password = password
        self.database = database

        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
        except Exception as e:
            print(f"Warning: Could not create neo4j driver: {e}")
            self.driver = None

        try:
            try:
                self.llm = GeminiLLM(model=llm_model_name, temperature=0.0)
            except GeminiUnavailable:
                print("Warning: Gemini LLM not available; Text->Cypher disabled.")
                self.llm = None
        except Exception as e:
            print(f"Warning: Could not initialize GeminiLLM: {e}")
            self.llm = None

        try:
            self.embedding_model = get_embedding_function()
        except Exception as e:
            print(f"Warning: Failed to initialize embedding model via helper: {e}")
            self.embedding_model = None

    def get_structured_retriever(self, query: str) -> Tuple[str, str]:
        """
        Translate `query` into Cypher using the LLM, execute it, and return
        (result_string, cypher_query). If unavailable, returns (error, "QUERY_FAILED").
        """
        if not self.llm or not self.driver:
            return ("Text->Cypher not available (LLM or driver missing).", "QUERY_FAILED")

        prompt = (
            "Translate the following natural language question into a valid Cypher query. "
            "Only output the Cypher query and nothing else. If the question cannot be answered with Cypher, output exactly 'NO_CYPHER'.\n\n"
            f"Question: {query}\n"
        )

        try:
            cypher_text = self.llm.generate(prompt)
            if not cypher_text or "NO_CYPHER" in cypher_text:
                return ("LLM could not produce a Cypher query.", "QUERY_FAILED")

            cypher_query = cypher_text.strip()

            with self.driver.session() as session:
                result = session.run(cypher_query)
                records = []
                for rec in result:
                    try:
                        records.append(dict(rec))
                    except Exception:
                        records.append(tuple(rec))

            return (str(records), cypher_query)
        # ... (your try block) ...
        except Exception as e:
            print("\n" + "="*50)
            print(f"!!! CRITICAL ERROR in get_structured_retriever !!!")
            traceback.print_exc()  # <--- ADD THIS LINE
            print("="*50 + "\n")
            return (f"Error running Cypher query: {e}", "QUERY_FAILED")

    # In D:\pharma\pharma_rag\services\neo4j_service.py

    def get_semantic_retriever(self) -> Callable[[str, int], List[str]]:
        """
        Returns a callable retriever(query, k) -> List[str].
        Uses a vector index for true semantic search.
        
        ASSUMPTION: You have a Neo4j vector index named 'document_chunk_embeddings'
        on the 'DocumentChunk' node and 'embedding' property.
        """
        
        # Check if the required services are available
        if not self.driver or not self.embedding_model:
            print("Warning: Neo4j driver or embedding model is not available.")
            def _mock_retriever(query: str, k: int = 5):
                return [f"Mock (services unavailable) Neo4j result for: {query}"]
            return _mock_retriever

        # --- THIS IS THE NEW VECTOR SEARCH FUNCTION ---
        def _neo4j_vector_retriever(query: str, k: int = 5) -> List[str]:
            
            # 1. Convert the query text to an embedding (vector)
            try:
                query_vector = self.embedding_model([query])[0]
            except Exception as e:
                print(f"Error generating query embedding: {e}")
                return [f"Failed to embed query: {e}"]

            # 2. Define the Cypher query for vector search
            # IMPORTANT: Replace 'document_chunk_embeddings' with the
            # name of your actual vector index in Neo4j.
            cypher = """
            CALL db.index.vector.queryNodes('document_chunk_embeddings', $k, $vector)
            YIELD node, score
            RETURN node.text AS text, score
            ORDER BY score DESC
            """
            
            # 3. Execute the query
            try:
                with self.driver.session() as session:
                    res = session.run(cypher, k=k, vector=query_vector)
                    rows = [
                        f"[Score: {record['score']:.4f}] {record['text']}" 
                        for record in res
                    ]
                    return rows
            except Exception as e:
                print(f"Error running vector search query: {e}")
                # This can happen if the index name is wrong or doesn't exist
                return [f"Neo4j vector search failed: {e}"]

        # Return the new vector retriever function
        return _neo4j_vector_retriever