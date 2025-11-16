from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
import os
import json
from dotenv import load_dotenv

# Import the necessary components
from crewai import LLM
from pharma_rag.services.embeddings import get_embedding_function
from pharma_rag.agents.master_agent import MasterAgent
from pharma_rag.utils.pdf_generator import create_pdf_report
# Assuming these services and tools are defined in your project structure:
from pharma_rag.services.chroma_service import ChromaService
from pharma_rag.services.neo4j_service import Neo4jGraphRAG
from pharma_rag.tools.graph_rag_tool import GraphRAGTool

load_dotenv()

# --- GLOBAL INITIALIZATION (Executed once on startup) ---

# 1. Initialize LLM/Embeddings
# Use a fast model for general reasoning/tools and a high-quality model for final synthesis
# Initialize Gemini LLM using CrewAI's LLM class (properly handles LiteLLM formatting)
# Note: For Gemini, the model name should include 'gemini/' prefix (e.g., "gemini/gemini-2.5-flash")
try:
    GENERAL_LLM = LLM(
        model=os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash"),
        temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.1")),
        api_key=os.getenv("GOOGLE_API_KEY")
    )
except Exception as e:
    print(f"FATAL: Failed to initialize Gemini LLM: {e}")
    print(f"Please ensure GOOGLE_API_KEY is set in your environment variables.")
    GENERAL_LLM = None
# Use the project's embedding factory which selects HF/Gemini/OpenAI or None (mock)
EMBEDDING_MODEL = get_embedding_function()

# 2. Initialize Services
try:
    # Check if LLM was initialized successfully
    if GENERAL_LLM is None:
        raise ValueError("LLM initialization failed. Cannot proceed with service initialization.")

    print("Initializing services...")

    # Use environment variables for credentials
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

    print("Initializing ChromaDB service...")
    chroma_service_instance = ChromaService()

    print("Initializing Neo4j service...")
    # Note: Neo4j service uses custom GeminiLLM wrapper (direct Google SDK calls)
    # It needs the model name WITHOUT the 'gemini/' prefix (that's only for LiteLLM)
    neo4j_llm_model = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")
    if neo4j_llm_model.startswith("gemini/"):
        neo4j_llm_model = neo4j_llm_model[7:]  # Strip 'gemini/' prefix

    neo4j_service_instance = Neo4jGraphRAG(
        uri=NEO4J_URI,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD,
        database=NEO4J_DATABASE,
        llm_model_name=neo4j_llm_model,
        embedding_model_name="text-embedding-004"
    )

    # 3. Initialize Tool (Dependency Injection)
    print("Initializing GraphRAG tool...")
    hybrid_rag_tool = GraphRAGTool(
        chroma_service=chroma_service_instance,
        neo4j_service=neo4j_service_instance
    )

    # 4. Initialize Master Agent
    print("Initializing Master Agent...")
    MASTER_AGENT_SERVICE = MasterAgent(
        llm=GENERAL_LLM,
        tools=[hybrid_rag_tool]
    )

    print("✓ All services initialized successfully!")

except Exception as e:
    import traceback
    print(f"FATAL: Failed to initialize services: {e}")
    traceback.print_exc()
    MASTER_AGENT_SERVICE = None # Flag that the service failed to start

# --------------------------------------------------------

class QueryInput(BaseModel):
    query: str
    target_geography: str

app = FastAPI(title="Pharma Innovation Agentic AI")

@app.post("/api/v1/research/run")
async def run_research_query(input: QueryInput):
    if MASTER_AGENT_SERVICE is None:
        raise HTTPException(status_code=503, detail="Agent services failed to initialize on startup.")

    full_query = f"{input.query} focusing on {input.target_geography}"
    
    try:
        # Run the Agentic Crew
        # The output is a structured JSON string from the Synthesis Task
        final_json_report_str = MASTER_AGENT_SERVICE.run_strategy(query=full_query)

        # Validate and clean up the JSON string (CrewAI output can sometimes be wrapped)
        # Attempt to parse and re-dump to ensure it's clean JSON
        try:
            report_data = json.loads(final_json_report_str)
            clean_json_str = json.dumps(report_data, indent=2)
        except json.JSONDecodeError:
            # If the LLM failed to output pure JSON, log and raise an error
            print(f"Agent failed to produce valid JSON output: {final_json_report_str}")
            raise ValueError("Agent failed to produce a structured report. Check agent logs.")

        # Generate the PDF and return it
        pdf_bytes = create_pdf_report(clean_json_str)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=Pharma_Opportunity_Report.pdf"
            }
        )

    except Exception as e:
        print(f"Error during agent execution: {e}")
        # Return a concise HTTP error
        raise HTTPException(status_code=500, detail=f"Research process failed: {str(e)}")