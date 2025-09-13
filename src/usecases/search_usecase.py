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
        # Modo literal mejorado: si la consulta va entre comillas, buscar frase exacta
        results = []
        import re
        match = re.match(r'^"(.+?)"$', query.strip())
        if match:
            phrase = match.group(1)
            phrase_norm = self.index_service.norm_words(phrase)
            # Buscar coincidencia exacta en texto original
            # Buscar coincidencia exacta insensible a mayúsculas y tildes
            exact_ids = [vid for vid, txt in self.index_service.text_by_id.items()
                         if self.index_service.norm_words(phrase) in self.index_service.norm_words(txt)]
            for vid in exact_ids:
                results.append({
                    "id": vid,
                    "score": 2.0,
                    "snippet": self.index_service.text_by_id.get(vid, ""),
                    "metadata": {"ref": self.index_service.ref_by_id.get(vid, "")}
                })
            return results[:top_k]
        # Si no hay comillas, buscar frase exacta y luego por tokens
        phrase_norm = self.index_service.norm_words(query)
        exact_ids = [vid for vid, txt in self.index_service.text_by_id.items()
                     if phrase_norm in self.index_service.norm_words(txt)]
        for vid in exact_ids:
            results.append({
                "id": vid,
                "score": 2.0,
                "snippet": self.index_service.text_by_id.get(vid, ""),
                "metadata": {"ref": self.index_service.ref_by_id.get(vid, "")}
            })
        tokens = self.index_service.tokenize_words(query)
        ids = set()
        for t in tokens:
            ids |= self.index_service.postings.get(t, set())
        for vid in list(ids):
            if vid not in exact_ids:
                results.append({
                    "id": vid,
                    "score": 1.0,
                    "snippet": self.index_service.text_by_id.get(vid, ""),
                    "metadata": {"ref": self.index_service.ref_by_id.get(vid, "")}
                })
        return results[:top_k]

# Ejemplo de inicialización (debe usarse en controller/router)
# index_service = InvertedIndexService(jsonl_path="versiculos.jsonl")
# usecase = SearchUseCase(index_service)
# usecase.search("amor de Dios", top_k=10)
