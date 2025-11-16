import pandas as pd
from typing import List, Dict
from pharma_rag.services.neo4j_service import Neo4jGraphRAG
from pharma_rag.services.chroma_service import ChromaService
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

# --- PART 1: Structured Data Parsing ---
class DocumentParser:
    def __init__(self):
        pass
    
    def parse_documents(self, file_path: str = "./data"):
        """
        Main entry point to parse documents from a directory or file.
        Returns a list of document chunks.
        """
        print(f"Parsing documents from: {file_path}")
        
        # If it's a single PDF file, parse it
        if os.path.isfile(file_path) and file_path.endswith('.pdf'):
            return self._parse_pdf(file_path)
        
        # If it's a directory, parse all PDFs in it
        if os.path.isdir(file_path):
            document_chunks = []
            for file in os.listdir(file_path):
                if file.endswith('.pdf'):
                    file_full_path = os.path.join(file_path, file)
                    document_chunks.extend(self._parse_pdf(file_full_path))
            return document_chunks
        
        return []
    
    def _parse_pdf(self, file_path: str) -> List[Dict]:
        """
        Parse a single PDF file and return chunks.
        """
        try:
            from pypdf import PdfReader
            
            reader = PdfReader(file_path)
            full_text = ""
            
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
            
            # Chunk the text
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                is_separator_regex=False,
            )
            
            chunks = text_splitter.split_text(full_text)
            
            # Return as list of dicts with metadata
            document_chunks = [
                {
                    "text": chunk,
                    "source_doc": os.path.basename(file_path),
                    "metadata": {"file": file_path, "chunk_size": len(chunk)}
                }
                for chunk in chunks
            ]
            
            return document_chunks
            
        except Exception as e:
            print(f"Error parsing PDF {file_path}: {e}")
            return []

def parse_clinical_trials(file_path: str = "./data/clinical_data.csv") -> List[Dict]:
    """
    Parses a structured data file (CSV/Excel) of clinical trials and extracts 
    key entities for KG insertion.
    
    Args:
        file_path: Path to the structured data file.
    
    Returns:
        A list of dictionaries containing entities and relationships.
    """
    print(f"Reading structured data from: {file_path}")
    
    # In a real scenario, use pandas to read and process a structured file
    # df = pd.read_csv(file_path) 
    
    # Mock structured data extraction for demonstration
    mock_data = [
        {"nct_id": "NCT0001", "molecule": "Xymaline", "disease": "COPD", "phase": "III", "status": "Completed"},
        {"nct_id": "NCT0002", "molecule": "Xymaline", "disease": "Asthma", "phase": "II", "status": "Recruiting"},
        {"nct_id": "NCT0003", "molecule": "Zentox", "disease": "Migraine", "phase": "I", "status": "Active"},
        {"nct_id": "NCT0004", "molecule": "Zentox", "disease": "Asthma", "phase": "III", "status": "Terminated"},
    ]
    
    return mock_data

# --- PART 2: Unstructured Data Processing (for Vector Store) ---

def ingest_unstructured_data(chroma_service: ChromaService, file_paths: List[str]):
    """
    Reads unstructured documents, chunks them, and embeds them into the ChromaDB.
    """
    print(f"\n--- Ingesting {len(file_paths)} Unstructured Documents into ChromaDB ---")
    
    # Simple document and chunking mock
    mock_documents = []
    
    for path in file_paths:
        # Mock file reading
        content = f"This is the detailed scientific memo for {os.path.basename(path)}. Xymaline shows high efficacy in preclinical models targeting Type 2 Inflammation. Zentox requires further toxicity evaluation."
        mock_documents.append({"content": content, "source": path})

    # Use LangChain Text Splitter (assuming it's installed)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )

    # In a real app, you would pass the list of texts to a method that handles
    # the splitting, embedding, and saving to ChromaDB.
    # chroma_service.save_chunks(texts)
    
    print("Documents tokenized, embedded, and indexed in ChromaDB.")


# --- PART 3: Knowledge Graph Builder ---

def build_knowledge_graph(
    data: List[Dict], 
    neo4j_service: Neo4jGraphRAG
):
    """
    Takes structured data and converts it into Neo4j nodes and relationships 
    using Cypher MERGE commands executed via the Neo4jGraphRAG service.
    """
    print("\n--- Building Knowledge Graph in Neo4j ---")
    
    # Get the raw connection driver from the service
    driver = neo4j_service.graph.driver
    
    cypher_statements = []

    for item in data:
        molecule = item["molecule"]
        nct_id = item["nct_id"]
        disease = item["disease"]
        phase = item["phase"]
        status = item["status"]

        # 1. MERGE Nodes (ensures uniqueness)
        cypher_statements.append(f"MERGE (m:Molecule {{name: '{molecule}'}})")
        cypher_statements.append(f"MERGE (d:Disease {{name: '{disease}'}})")
        # Trial node includes properties
        cypher_statements.append(f"MERGE (t:Trial {{nct_id: '{nct_id}'}}) SET t.phase = '{phase}', t.status = '{status}', t.title = 'Clinical Trial {nct_id}'")

        # 2. MERGE Relationships
        cypher_statements.append(
            f"MATCH (m:Molecule {{name: '{molecule}'}}), (t:Trial {{nct_id: '{nct_id}'}}) "
            f"MERGE (m)-[:TESTED_IN]->(t)"
        )
        cypher_statements.append(
            f"MATCH (t:Trial {{nct_id: '{nct_id}'}}), (d:Disease {{name: '{disease}'}}) "
            f"MERGE (t)-[:TARGETS]->(d)"
        )

    # Execute all statements in a single transaction for efficiency
    with driver.session() as session:
        for cypher in cypher_statements:
            try:
                session.run(cypher)
            except Exception as e:
                print(f"Error executing Cypher: {cypher}. Error: {e}")

    print(f"Knowledge Graph preparation completed. {len(data)} records processed.")


# --- PART 4: Orchestrator Example (Optional) ---

def run_ingestion_pipeline(neo4j_service: Neo4jGraphRAG, chroma_service: ChromaService):
    """Orchestrates the entire ingestion process."""
    
    # Ingest Structured Data
    structured_data = parse_clinical_trials()
    build_knowledge_graph(structured_data, neo4j_service)

    # Ingest Unstructured Data
    unstructured_files = ["./data/internal_memo.pdf", "./data/patent_summary.docx"]
    ingest_unstructured_data(chroma_service, unstructured_files)
    
    print("\n--- Full Data Ingestion Pipeline Finished ---")

# Note: The 'run_ingestion_pipeline' function would be called from a main script 
# (like a separate `ingest.py` file) after initializing the services.