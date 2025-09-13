import httpx
import os
from typing import List

from typing import Optional

class OllamaEmbedder:
    def __init__(self, base_url: Optional[str] = None, model: str = "nomic-embed-text"):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/api/embeddings")
        self.model = model

    async def embed(self, text: str) -> List[float]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                self.base_url,
                json={"model": self.model, "prompt": text}
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
