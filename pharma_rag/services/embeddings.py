import os
from typing import Optional

from langchain_huggingface import HuggingFaceEmbeddings

embedding = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except Exception:
    HuggingFaceEmbeddings = None

try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
except Exception:
    GoogleGenerativeAIEmbeddings = None

try:
    from langchain_openai import OpenAIEmbeddings
except Exception:
    OpenAIEmbeddings = None


def get_embedding_function() -> Optional[object]:
    """Return an embeddings object (HuggingFace / Google / OpenAI) according to env vars.

    Priority:
      1. HuggingFace if `USE_HF_EMBEDDINGS` is true or `HF_MODEL_NAME` is set
      2. Google Generative AI if `GEMINI_API_KEY` is set
      3. OpenAI if `OPENAI_API_KEY` is set
      4. None (mock) otherwise
    """
    use_hf = os.getenv("USE_HF_EMBEDDINGS", "false").lower() in ("1", "true", "yes")
    hf_model = os.getenv("HF_MODEL_NAME")
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    # HuggingFace
    if (use_hf or hf_model) and HuggingFaceEmbeddings is not None:
        model_name = hf_model or "sentence-transformers/all-MiniLM-L6-v2"
        try:
            return HuggingFaceEmbeddings(model_name=model_name)
        except Exception as e:
            print(f"Warning: Failed to initialize HuggingFaceEmbeddings: {e}")

    # Google Generative AI
    if gemini_key and GoogleGenerativeAIEmbeddings is not None:
        try:
            return GoogleGenerativeAIEmbeddings(model=os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-004"), api_key=gemini_key)
        except Exception as e:
            print(f"Warning: Failed to initialize GoogleGenerativeAIEmbeddings: {e}")

    # OpenAI
    if openai_key and OpenAIEmbeddings is not None:
        try:
            return OpenAIEmbeddings()
        except Exception as e:
            print(f"Warning: Failed to initialize OpenAIEmbeddings: {e}")

    print("No embeddings backend initialized (HF/Gemini/OpenAI not available). Using mock mode.")
    return None
