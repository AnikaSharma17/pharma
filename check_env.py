#!/usr/bin/env python3
"""
Diagnostic script to check environment setup for pharma application.
Run this before starting the server to verify all required environment variables are set.
"""
import os
from dotenv import load_dotenv

print("=" * 60)
print("PHARMA APPLICATION ENVIRONMENT CHECK")
print("=" * 60)

# Load .env file if it exists
env_file_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file_path):
    print(f"✓ Found .env file at: {env_file_path}")
    load_dotenv()
else:
    print(f"✗ No .env file found at: {env_file_path}")
    print(f"  Please create it by copying .env.example:")
    print(f"  cp .env.example .env")
    print()

print("\nChecking required environment variables:")
print("-" * 60)

# Check GOOGLE_API_KEY (REQUIRED)
google_api_key = os.getenv("GOOGLE_API_KEY")
if google_api_key:
    print(f"✓ GOOGLE_API_KEY is set (length: {len(google_api_key)} chars)")
else:
    print("✗ GOOGLE_API_KEY is NOT set (REQUIRED)")
    print("  Get your API key from: https://makersuite.google.com/app/apikey")

# Check optional variables
gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
print(f"  GEMINI_MODEL: {gemini_model} {'(default)' if not os.getenv('GEMINI_MODEL') else ''}")

gemini_temp = os.getenv("GEMINI_TEMPERATURE", "0.1")
print(f"  GEMINI_TEMPERATURE: {gemini_temp} {'(default)' if not os.getenv('GEMINI_TEMPERATURE') else ''}")

# Check Neo4j variables
neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
neo4j_user = os.getenv("NEO4J_USER", "neo4j")
neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

print(f"\n  NEO4J_URI: {neo4j_uri} {'(default)' if not os.getenv('NEO4J_URI') else ''}")
print(f"  NEO4J_USER: {neo4j_user} {'(default)' if not os.getenv('NEO4J_USER') else ''}")
print(f"  NEO4J_PASSWORD: {'***' if neo4j_password else 'NOT SET'} {'(default)' if not os.getenv('NEO4J_PASSWORD') else ''}")
print(f"  NEO4J_DATABASE: {neo4j_database} {'(default)' if not os.getenv('NEO4J_DATABASE') else ''}")

print("\n" + "=" * 60)

# Summary
if google_api_key:
    print("✓ READY TO START - All required variables are set")
    print("\nYou can now start the server with:")
    print("  uvicorn pharma_rag.main:app --reload --host 127.0.0.1 --port 8000")
else:
    print("✗ NOT READY - Missing required environment variables")
    print("\nSteps to fix:")
    print("  1. Copy .env.example to .env:")
    print("     cp .env.example .env")
    print("  2. Edit .env and set GOOGLE_API_KEY=your_actual_api_key")
    print("  3. Restart the server")

print("=" * 60)
