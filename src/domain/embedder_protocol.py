from typing import Protocol, List

class EmbedderProtocol(Protocol):
    async def embed(self, text: str) -> List[float]:
        ...
