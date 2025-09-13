from src.services.inverted_index import InvertedIndexService
from typing import List, Dict, Any

class SearchUseCase:
    """
    Orquesta la búsqueda literal y semántica, aplicando optimizaciones y principios SOLID.
    """
    def __init__(self, index_service: InvertedIndexService):
        self.index_service = index_service

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        # Ejemplo: solo búsqueda literal por ahora
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
