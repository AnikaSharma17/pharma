
**Project Overview**

- **Name:** `pharma` : An agentic Research-Assistant and RAG (Retrieval-Augmented Generation) toolkit focused on pharmaceutical repurposing and opportunity discovery.
- **Purpose:** Orchestrates agent teams to ingest documents, build a knowledge graph, run semantic + structured retrieval, and produce executive PDF reports with prioritized repurposing opportunities.

**Quick Start**

- **Install (recommended in a virtual env):**

	```powershell
	python -m venv .venv
	.\.venv\Scripts\Activate.ps1
	pip install -r pharma_rag\requirements.txt
	```

- **Environment variables:** Create a `.env` in the repo root or export the following before running:

	- `GEMINI_API_KEY` (or `OPENAI_API_KEY`) — LLM embeddings/generation API key
	````markdown

	**Project Overview**

	- **Name:** `pharma` — an agentic Research Assistant and RAG (Retrieval-Augmented Generation) toolkit focused on pharmaceutical opportunity discovery and repurposing.
	- **Purpose:** Ingests documents, builds a knowledge graph, provides semantic + structured retrieval, and orchestrates CrewAI agents to synthesize structured reports (PDF output).

	**Quick Start**

	- **Create and activate a venv (Windows PowerShell):**

	  ```powershell
	  python -m venv .venv
	  .\.venv\Scripts\Activate.ps1
	  ```

	- **Install dependencies:**

	  ```powershell
	  pip install -r pharma_rag\requirements.txt
	  ```

	- **Environment variables:** Create a `.env` at the repo root (or export these in your shell):

	  - **`GEMINI_API_KEY`**: Google Gemini / GenAI credentials (if using Gemini).  
	  - **`USE_HF_EMBEDDINGS`**: `true` to prefer local Hugging Face embeddings.  
	  - **`HF_MODEL_NAME`**: e.g. `sentence-transformers/all-MiniLM-L6-v2` (when using HF embeddings).  
	  - **`NEO4J_URI`**: e.g. `bolt://localhost:7687`  
	  - **`NEO4J_USER`** / **`NEO4J_PASSWORD`**: Neo4j credentials  

	  Notes: the app will degrade gracefully if an embedding provider or LLM is not configured (it may run in mock mode). If you see "Your default credentials were not found" for Gemini, configure Google ADC or set `GEMINI_API_KEY` per your provider's docs.

	- **Run the API (development):**

	  ```powershell
	  D:/pharma/venv/Scripts/python.exe -m uvicorn pharma_rag.main:app --reload --host 127.0.0.1 --port 8000
	  ```

	  Or run the module directly (note: `main.py` does not auto-run uvicorn unless you add an entry):

	  ```powershell
	  python -m pharma_rag.main
	  ```

	**Architecture & Key Components**

	- **Entry point (API):** `pharma_rag/main.py` — bootstraps LLM, embedding factory, `ChromaService`, `Neo4jGraphRAG`, `GraphRAGTool`, and the `MasterAgent`. Exposes `POST /api/v1/research/run`.

	- **Agents (CrewAI):**
	  - `pharma_rag/agents/master_agent.py` — orchestrates tasks and synthesis.  
	  - `pharma_rag/agents/worker_agents.py` — worker agents (clinical/patent, market, internal knowledge, report generation) and tool wiring.

	- **RAG & Services:**
	  - `pharma_rag/services/chroma_service.py` — Chroma vector store wrapper (semantic search + ingestion). Currently uses a LangChain wrapper; can be migrated to `chromadb` client if preferred.  
	  - `pharma_rag/services/neo4j_service.py` — Neo4j integration using `neo4j.Driver` and a small Text→Cypher flow driven by `GeminiLLM` (LangChain-free in the current branch).  
	  - `pharma_rag/services/embeddings.py` — embedding factory that chooses HF/Gemini/OpenAI backends.  

	- **Tools & Utilities:**
	  - `pharma_rag/tools/graph_rag_tool.py` — unified tool that routes requests to structured (Neo4j) or semantic (Chroma) retrievers.  
	  - `pharma_rag/utils/document_parser.py` — PDF/text chunking and metadata extraction.  
	  - `pharma_rag/utils/pdf_generator.py` — creates PDF bytes from the final JSON (currently a stub).  
	  - `pharma_rag/utils/report_schema.py` — Pydantic models for final structured output.

	- **ADK / A2A (Agent-to-Agent):** The repo includes an ADK adapter so a native ADK agent (if installed) can be invoked; when ADK is not present the code falls back to a CrewAI-based adapter.

	**How the request flow works**

	- Client posts a `query` + `target_geography` to `/api/v1/research/run`.  
	- The `MasterAgent` creates tasks and delegates to worker agents which call `GraphRAGTool` to run either:
	  - a structured Cypher query against Neo4j (via `Neo4jGraphRAG.get_structured_retriever`) or
	  - a semantic document search against Chroma (via `ChromaService.semantic_search`).  
	- The results are synthesized into a `FinalReport` (Pydantic), converted to PDF bytes, and returned as an attachment.

	**Example request**

	```powershell
	curl -X POST "http://127.0.0.1:8000/api/v1/research/run" -H "Content-Type: application/json" -d "{\"query\":\"aspirin repurposing opportunities\",\"target_geography\":\"US\"}"
	```

	**Ingestion (documents → Chroma + Neo4j)**

	- Run the ingestion pipeline to parse and ingest documents into Chroma and populate Neo4j:

	```powershell
	python pharma_rag/ingestion_pipeline.py --data_dir D:\pharma\data\raw_docs
	```

	Pipeline steps: parse → chunk → embed → store in Chroma → extract relations → write Cypher to Neo4j.

	**Troubleshooting & Common Messages**

	- **`ChromaDB initialized with embedding function.`** — Chroma detected an embedding backend and initialized the vector store successfully.  
	- **`ChromaDB initialized in mock mode (no embeddings).`** — No embedding function configured; semantic search will return mock results.  
	- **`Your default credentials were not found`** — Google ADC (Gemini) credentials are missing; set ADC or configure `GEMINI_API_KEY` per your setup.  
	- **Neo4j connection errors** — check `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` and ensure the DB is running.  
	- **Agent tool validation errors** — Agents expect CrewAI `Tool` instances (not plain functions). The current code wraps instance tools correctly; if you see model validation errors, they typically indicate a mis-wired tool in `agents/`.

	**Development notes & recommended next steps**

	- Consolidate embedding selection by moving `chroma_service` to use the central `services/embeddings.get_embedding_function()` (recommended; currently `chroma_service` contains a small local helper).  
	- Optionally migrate `chroma_service` off LangChain and use the `chromadb` client directly to remove a LangChain dependency.  
	- Add stricter validation of LLM-generated Cypher before executing against Neo4j (for safety).  
	- Replace the PDF stub with `reportlab` or `weasyprint` for production-quality PDFs.

	**Project layout (high level)**

	- `pharma_rag/` — package
	  - `agents/` — CrewAI agent logic  
	  - `services/` — Chroma/Neo4j/embedding/Gemini helpers  
	  - `tools/` — Graph-RAG tool  
	  - `utils/` — parsers, pdf generator, schema models  
	- `data/` — ingestion source data  
	- `Dockerfile`, `run.sh`, `pyproject.toml`

	**License & contribution**

	- No license file is included. Add a `LICENSE` if you plan to publish.  
	- Contributions: open issues/PRs; for large changes open a design issue first.

	---
	Generated on: 2025-11-16
	````

