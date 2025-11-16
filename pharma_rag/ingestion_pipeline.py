import os
import argparse
# Assuming these services and utilities exist in your current structure
from pharma_rag.utils.document_parser import DocumentParser
from pharma_rag.services.chroma_service import ChromaService
from pharma_rag.services.neo4j_service import Neo4jGraphRAG
from pharma_rag.utils.document_parser import build_knowledge_graph, parse_clinical_trials

# Define the root path where your raw documents are stored (e.g., PHARMA/data/raw_docs)
my_file_path = r"D:\pharma\data\raw_docs\209637s035,209637s037lbl.pdf"
#DEFAULT_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw_docs')

def run_ingestion(data_dir: str):
    """
    Orchestrates the data ingestion process:
    1. Parses and chunks documents.
    2. Loads text chunks into ChromaDB (Vector Store for semantic search).
    3. Loads entities and relationships into Neo4j (Knowledge Graph for structured reasoning).
    """
    print(f"--- Starting Data Ingestion Pipeline from directory: {data_dir} ---")
    
    # 1. Initialization and Document Parsing
    parser = DocumentParser()
    print("Parsing and chunking documents...")
    
    # This function should read files, clean them, chunk them, and return a list of document chunks.
    # Each chunk should be a dictionary containing at least 'text', 'source_doc', and 'metadata'.
    try:
        document_chunks = parser.parse_documents(data_dir)
        if not document_chunks:
            print("No document chunks were processed. Please check the data directory and parser settings.")
            return
        print(f"Successfully processed {len(document_chunks)} chunks.")
    except Exception as e:
        print(f"Error during document parsing: {e}")
        return

    # 2. Vector Store Loading (ChromaDB)
    chroma_service = ChromaService()
    print("Loading chunks into ChromaDB...")
    try:
        chroma_service.load_chunks(document_chunks)
        print("ChromaDB ingestion complete.")
    except Exception as e:
        print(f"Error during ChromaDB ingestion: {e}")

    # 3. Knowledge Graph Loading (Neo4j)
    # Read Neo4j + model configuration from environment variables
    neo4j_uri = os.getenv("NEO4J_URI")
    # Support both NEO4J_USER and NEO4J_USERNAME from different env conventions
    neo4j_user = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    neo4j_db = os.getenv("NEO4J_DATABASE", "neo4j")
    llm_model = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")
    embedding_model = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-004")

    if not (neo4j_uri and neo4j_user and neo4j_password):
        print("Skipping Neo4j ingestion: missing NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD environment variables.")
        print("To enable Neo4j loading, set the environment variables and re-run: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
    else:
        try:
            neo4j_service = Neo4jGraphRAG(
                uri=neo4j_uri,
                user=neo4j_user,
                password=neo4j_password,
                database=neo4j_db,
                llm_model_name=llm_model,
                embedding_model_name=embedding_model,
            )
            print("Extracting entities and loading into Neo4j...")
            # Build knowledge graph from structured clinical trial data (not raw text chunks)
            structured_data = parse_clinical_trials()
            build_knowledge_graph(structured_data, neo4j_service)
            print("Neo4j ingestion complete.")
        except Exception as e:
            print(f"Error during Neo4j ingestion: {e}")

    print("--- Data Ingestion Pipeline Finished ---")


if __name__ == '__main__':
    # Allows running the script from the command line with a custom data path
    parser = argparse.ArgumentParser(description="Run the Pharmaceutical RAG Ingestion Pipeline.")
    parser.add_argument(
        '--data_dir', 
        type=str, 
        default=my_file_path, 
        help=f"Path to the directory containing raw documents. Defaults to: {my_file_path}"
    )
    args = parser.parse_args()
    
    # Create the data directory if it doesn't exist
    if not os.path.exists(args.data_dir):
        os.makedirs(args.data_dir)
        print(f"Created data directory: {args.data_dir}. Place your raw documents (PDFs, TXT, etc.) here.")
    else:
        run_ingestion(args.data_dir)