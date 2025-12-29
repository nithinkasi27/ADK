import os
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv
load_dotenv()

def get_llm(temp=0.1, tokens=3000):
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT not set")

    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    return ChatVertexAI(
        model_name="gemini-2.5-flash",
        project=project,
        location=location,
        temperature=temp,
        max_output_tokens=tokens,
    )