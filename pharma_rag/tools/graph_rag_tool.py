from crewai import Agent
from crewai.tools import BaseTool
from pharma_rag.services.chroma_service import ChromaService
from pharma_rag.services.neo4j_service import Neo4jGraphRAG
from typing import Type, List
from pydantic import BaseModel, Field


# --- Define the required input schema for the tool ---
class GraphRAGToolInput(BaseModel):
    query: str = Field(description="A concise question requiring either structured relational reasoning OR deep textual context.")
    tool_type: str = Field(description="The type of search to perform. Must be 'structured' (for Neo4j KG/Cypher) or 'semantic' (for Chroma/vector search).")


class GraphRAGTool(BaseTool):   # <-- FIXED HERE (ONLY CHANGE)
    """
    A unified tool that performs either structured (Graph/Cypher) or semantic 
    (Vector/Chroma) search based on the query.
    """
    name: str = "Hybrid Graph-RAG Search Tool"
    description: str = (
        "A powerful tool for searching knowledge. It performs a **STRUCTURED GRAPH QUERY** (Cypher) for "
        "relational facts, counts, and multi-hop reasoning, or a **SEMANTIC DOCUMENT SEARCH** (Vector) for "
        "deep textual context. The agent MUST decide which type of search is appropriate."
    )

    # Dependency injection
    chroma_service: ChromaService = Field(description="Initialized instance of the Chroma Service.")
    neo4j_service: Neo4jGraphRAG = Field(description="Initialized instance of the Neo4j Graph RAG Service.")

    # Input schema
    args_schema: Type[BaseModel] = GraphRAGToolInput

    def _run(self, query: str, tool_type: str) -> str:
        """
        The primary execution method. Routes the query based on the selected tool_type.
        """
        if tool_type == "structured":
            return self._run_graph_query(query)
        else:
            return self._run_semantic_search(query)

    def _run_semantic_search(self, query: str) -> str:
        """Internal method for executing Semantic Search via Chroma."""
        results: List[str] = self.chroma_service.semantic_search(query, k=5)

        if not results:
            return "No relevant unstructured documents found for this query."

        return "Retrieved unstructured context:\n" + "\n---\n".join(results)

    def _run_graph_query(self, query: str) -> str:
        """Internal method for executing Structured Graph Query via Neo4j (Text2Cypher)."""
        try:
            structured_answer, cypher_info = self.neo4j_service.get_structured_retriever(query)

            if "QUERY_FAILED" in cypher_info:
                return f"Graph Query Failed. Reason: {structured_answer}"

            return f"Graph Query Result:\n{structured_answer}"

        except Exception as e:
            return f"Unexpected Error in graph query: {type(e).__name__}: {str(e)}"
