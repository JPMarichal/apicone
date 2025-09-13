from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from typing import List, Optional, Dict, Any, Tuple
from src.usecases.search_usecase import SearchUseCase
from src.services.inverted_index import InvertedIndexService
import os
from datetime import datetime

class SearchRequest(BaseModel):
    q: str = Field(..., description="Consulta de búsqueda")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filtros opcionales")
    top_k: Optional[int] = Field(10, description="Número máximo de resultados")
    include_snippets: Optional[bool] = Field(False, description="Incluir fragmentos de texto")
    mode: Optional[str] = Field("literal", description="Modo de búsqueda: 'literal' o 'semantic'")

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

# Inicialización de adaptadores para búsqueda semántica
from src.services.embedder_ollama import OllamaEmbedder
from src.adapters.pinecone_adapter import PineconeAdapter

jsonl_path = os.getenv("JSONL_PATH", "versiculos.jsonl")
index_service = InvertedIndexService(jsonl_path=jsonl_path)

# Configuración Pinecone
pinecone_api_key = os.getenv("PINECONE_API_KEY", "")
pinecone_env = os.getenv("PINECONE_ENVIRONMENT", "us-east1-gcp")
pinecone_index = os.getenv("PINECONE_INDEX", "escrituras")
pinecone_namespace = os.getenv("PINECONE_NAMESPACE", "es")

embedder = OllamaEmbedder()
pinecone_adapter = PineconeAdapter(
    api_key=pinecone_api_key,
    environment=pinecone_env,
    index_name=pinecone_index,
    namespace=pinecone_namespace
)

search_usecase = SearchUseCase(index_service, embedder=embedder, pinecone_adapter=pinecone_adapter)


import asyncio

@router.post("/search", response_model=SearchResponse)
async def search_endpoint(request: SearchRequest):
    """
    Endpoint de búsqueda literal y semántica.
    Aplica optimizaciones y patrones SOLID en la lógica interna.
    """
    results = await search_usecase.search(
        request.q,
        top_k=request.top_k or 10,
        mode=request.mode or "literal"
    )
    return SearchResponse(results=[SearchResult(**r) for r in results], query_embedding=None)


class EmbeddingUpsertItem(BaseModel):
    id: Optional[str]
    text: str
    metadata: Optional[Dict[str, Any]] = None

class EmbeddingUpsertRequest(BaseModel):
    items: List[EmbeddingUpsertItem]
    namespace: Optional[str] = None

class EmbeddingUpsertResponse(BaseModel):
    upserted: int
    failed: List[Dict[str, Any]]


@router.post("/embeddings/upsert", response_model=EmbeddingUpsertResponse)
async def embeddings_upsert_endpoint(request: EmbeddingUpsertRequest):
    """
    Upsert de embeddings en Pinecone. Genera embedding con Ollama y almacena en el vector DB.
    """
    upserted = 0
    failed: List[Dict[str, Any]] = []
    vectors: List[Tuple[str, List[float], Dict[str, Any]]] = []
    for item in request.items:
        try:
            embedding = await embedder.embed(item.text)
            vid = item.id if item.id else str(abs(hash(item.text + str(item.metadata or {}))))
            # Pinecone espera: (id, values, metadata)
            vectors.append((vid, embedding, item.metadata or {}))
        except Exception as e:
            failed.append({"id": item.id, "reason": str(e)})
    # Upsert en Pinecone
    if vectors:
        try:
            pinecone_adapter.index.upsert(vectors=vectors, namespace=request.namespace or pinecone_namespace)
            upserted = len(vectors)
        except Exception as e:
            for v in vectors:
                failed.append({"id": v[0], "reason": f"Upsert error: {str(e)}"})
    return EmbeddingUpsertResponse(upserted=upserted, failed=failed)


class DocumentResponse(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str

@router.get("/documents/{id}", response_model=DocumentResponse)
async def get_document_by_id(id: str):
    """
    Devuelve el documento por ID, usando el corpus local como fuente inicial.
    """
    # Buscar en corpus local (versiculos.jsonl)
    import json
    import os
    corpus_path = os.path.join(os.path.dirname(__file__), '../../versiculos.jsonl')
    try:
        with open(corpus_path, encoding='utf-8') as f:
            for line in f:
                doc = json.loads(line)
                if doc.get('id') == id:
                    from datetime import timezone
                    now = datetime.now(timezone.utc).isoformat()
                    return DocumentResponse(
                        id=doc['id'],
                        text=doc['text'],
                        metadata=doc.get('metadata', {}),
                        created_at=doc.get('created_at', now),
                        updated_at=doc.get('updated_at', now)
                    )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo corpus: {str(e)}")
    raise HTTPException(status_code=404, detail="Documento no encontrado")
