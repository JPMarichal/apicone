from src.services.inverted_index import InvertedIndexService
from typing import List, Dict, Any


from src.services.embedder_ollama import OllamaEmbedder
from src.adapters.pinecone_adapter import PineconeAdapter

class SearchUseCase:
    """
    Orquesta la búsqueda literal y semántica, aplicando optimizaciones y principios SOLID.
    """
    def __init__(self, index_service: InvertedIndexService, embedder: OllamaEmbedder = None, pinecone_adapter: PineconeAdapter = None):
        self.index_service = index_service
        self.embedder = embedder
        self.pinecone_adapter = pinecone_adapter

    async def search(self, query: str, top_k: int = 10, mode: str = "literal") -> List[Dict[str, Any]]:
        if mode == "semantic" and self.embedder and self.pinecone_adapter:
            embedding = await self.embedder.embed(query)
            results = self.pinecone_adapter.query(embedding, top_k=top_k)
            return results
        # Modo literal (por defecto)
        results = []
        tokens = self.index_service.tokenize_words(query)
        ids = set()
        for t in tokens:
            ids |= self.index_service.postings.get(t, set())
        for vid in list(ids)[:top_k]:
            results.append({
                "id": vid,
                "score": 1.0,
                "snippet": self.index_service.text_by_id.get(vid, ""),
                "metadata": {"ref": self.index_service.ref_by_id.get(vid, "")}
            })
        return results

# Ejemplo de inicialización (debe usarse en controller/router)
# index_service = InvertedIndexService(jsonl_path="versiculos.jsonl")
# usecase = SearchUseCase(index_service)
# usecase.search("amor de Dios", top_k=10)
