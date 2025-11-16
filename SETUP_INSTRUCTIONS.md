# Setup Instructions - Fix "Agent services failed to initialize" Error

## Problem

You're getting a **503 Service Unavailable** error with the message:
```json
{
  "detail": "Agent services failed to initialize on startup."
}
```

## Root Cause

The `.env` file does not exist in your project root, so the required `GOOGLE_API_KEY` environment variable is not set. Without this, the agent services cannot initialize.

## Solution

Follow these steps to fix the issue:

### Step 1: Create the .env file

In your project root directory (`/home/user/pharma`), create a `.env` file:

```bash
cp .env.example .env
```

Or manually create it:

```bash
cat > .env << 'EOF'
# Google Gemini API Configuration
# Get your API key from: https://makersuite.google.com/app/apikey
GOOGLE_API_KEY=your_google_api_key_here

# Gemini Model Configuration
# Note: Model name must include 'gemini/' prefix for LiteLLM compatibility (used by CrewAI)
GEMINI_MODEL=gemini/gemini-2.5-flash
GEMINI_TEMPERATURE=0.1

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password_here
NEO4J_DATABASE=neo4j
EOF
```

### Step 2: Get Your Google API Key

1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated API key

### Step 3: Edit the .env file

Open the `.env` file and replace `your_google_api_key_here` with your actual API key:

```bash
GOOGLE_API_KEY=AIzaSyC_your_actual_api_key_here
```

**Important:** Keep this key secure and never commit it to version control!

### Step 4: Set Neo4j Password (Optional)

If you're using Neo4j, also update the `NEO4J_PASSWORD` in the `.env` file:

```bash
NEO4J_PASSWORD=your_actual_neo4j_password
```

If Neo4j is not running or configured, the application will print warnings but should still start (some features may not work).

### Step 5: Restart the Server

Stop your current server (Ctrl+C) and restart it:

```bash
uvicorn pharma_rag.main:app --reload --host 127.0.0.1 --port 8000
```

### Step 6: Verify Successful Startup

You should see these messages in the server logs:

```
Initializing services...
Initializing ChromaDB service...
ChromaDB initialized with embedding function.
Initializing Neo4j service...
Initializing GraphRAG tool...
Initializing Master Agent...
✓ All services initialized successfully!
```

If you see these messages, the server is ready!

### Step 7: Test the API

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/research/run" \
  -H "Content-Type: application/json" \
  -d '{"query":"aspirin repurposing opportunities","target_geography":"US"}'
```

## Troubleshooting

### Still getting 503 error?

1. **Check if .env file exists:**
   ```bash
   ls -la .env
   ```

2. **Verify GOOGLE_API_KEY is set:**
   ```bash
   grep GOOGLE_API_KEY .env
   ```

3. **Check server startup logs** for specific error messages

4. **Verify API key is valid:** Make a test request to Google's API

### Common Error Messages

- **"FATAL: Failed to initialize Gemini LLM"** - Your `GOOGLE_API_KEY` is missing or invalid
- **"ModuleNotFoundError"** - Dependencies not installed. Run: `pip install -r requirements.txt`
- **Neo4j connection errors** - Check Neo4j is running and credentials are correct

## Quick Reference

| Environment Variable | Required | Default | Description |
|---------------------|----------|---------|-------------|
| `GOOGLE_API_KEY` | **YES** | None | Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini/gemini-2.5-flash` | Gemini model name (with provider prefix) |
| `GEMINI_TEMPERATURE` | No | `0.1` | LLM temperature |
| `NEO4J_URI` | No | `bolt://localhost:7687` | Neo4j connection URI |
| `NEO4J_USER` | No | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | No | `password` | Neo4j password |
| `NEO4J_DATABASE` | No | `neo4j` | Neo4j database name |

---

**Need more help?** Check the main README.md for complete documentation.
