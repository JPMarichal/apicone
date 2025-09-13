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

    def canon_sort_key(self, ref: str) -> tuple:
        # Orden canónico: AT, NT, BM, DyC, PGP
        canon = [
            "Génesis","Éxodo","Levítico","Números","Deuteronomio","Josué","Jueces","Rut",
            "1 Samuel","2 Samuel","1 Reyes","2 Reyes","1 Crónicas","2 Crónicas","Esdras","Nehemías","Ester",
            "Job","Salmos","Proverbios","Eclesiastés","Cantares","Isaías","Jeremías","Lamentaciones",
            "Ezequiel","Daniel","Oseas","Joel","Amós","Abdías","Jonás","Miqueas","Nahúm","Habacuc",
            "Sofonías","Hageo","Zacarías","Malaquías",
            "Mateo","Marcos","Lucas","Juan","Hechos","Romanos","1 Corintios","2 Corintios","Gálatas",
            "Efesios","Filipenses","Colosenses","1 Tesalonicenses","2 Tesalonicenses","1 Timoteo",
            "2 Timoteo","Tito","Filemón","Hebreos","Santiago","1 Pedro","2 Pedro","1 Juan","2 Juan",
            "3 Juan","Judas","Apocalipsis",
            "1 Nefi","2 Nefi","Jacob","Enós","Jarom","Omni","Palabras de Mormón","Mosíah","Alma",
            "Helamán","3 Nefi","4 Nefi","Mormón","Éter","Moroni",
            "Doctrina y Convenios",
            "Moisés","Abraham","José Smith—Mateo","José Smith—Historia","Artículos de Fe"
        ]
        import re
        def norm_book_key(s):
            s = s.replace("—","-").replace("–","-")
            s = s.lower()
            return re.sub(r"\s+", " ", s).strip()
        book, chap, verse = None, 0, 0
        m = re.match(r"^(.+?)\s+(\d+)(?::(\d+))?$", ref.strip())
        if m:
            book = m.group(1).strip()
            chap = int(m.group(2))
            verse = int(m.group(3) or 0)
        idx = {norm_book_key(name): i for i, name in enumerate(canon)}
        order = idx.get(norm_book_key(book or ref), len(canon)+1000)
        return (order, chap, verse)

    async def search(self, query: str, top_k: int = 10, mode: str = "literal") -> List[Dict[str, Any]]:
        if mode == "semantic" and self.embedder and self.pinecone_adapter:
            embedding = await self.embedder.embed(query)
            results = self.pinecone_adapter.query(embedding, top_k=top_k)
            # Ordenar por orden canónico
            results.sort(key=lambda r: self.canon_sort_key(r.get("ref", "")))
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
