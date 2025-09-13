import httpx
from typing import List

class OllamaEmbedder:
    def __init__(self, base_url: str = "http://localhost:11434/api/embeddings", model: str = "llama2"):
        self.base_url = base_url
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
