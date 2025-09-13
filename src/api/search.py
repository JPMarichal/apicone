from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from src.usecases.search_usecase import SearchUseCase
from src.services.inverted_index import InvertedIndexService
import os

class SearchRequest(BaseModel):
    q: str = Field(..., description="Consulta de búsqueda")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filtros opcionales")
    top_k: Optional[int] = Field(10, description="Número máximo de resultados")
    include_snippets: Optional[bool] = Field(False, description="Incluir fragmentos de texto")

class SearchResult(BaseModel):
    id: str
    score: float
    snippet: Optional[str]
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query_embedding: Optional[List[float]]

router = APIRouter(prefix="/api/v1", tags=["search"])

# Inicialización del índice inverso y usecase (singleton)
jsonl_path = os.getenv("JSONL_PATH", "versiculos.jsonl")
index_service = InvertedIndexService(jsonl_path=jsonl_path)
search_usecase = SearchUseCase(index_service)

@router.post("/search", response_model=SearchResponse)
def search_endpoint(request: SearchRequest):
    """
    Endpoint de búsqueda literal y semántica.
    Aplica optimizaciones y patrones SOLID en la lógica interna.
    """
    results = search_usecase.search(request.q, top_k=request.top_k or 10)
    return SearchResponse(results=[SearchResult(**r) for r in results], query_embedding=None)
