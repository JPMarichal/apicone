from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from typing import List, Optional, Dict, Any, Tuple
from src.usecases.search_usecase import SearchUseCase
from src.services.inverted_index import InvertedIndexService
import os
from datetime import datetime
import uuid
import re

class SearchRequest(BaseModel):
    """
    Modelo de entrada para búsqueda de versículos.
    Permite búsqueda literal o semántica, con filtros y paginación.
    """
    q: str = Field(..., description="Consulta de búsqueda")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filtros opcionales")
    top_k: Optional[int] = Field(10, description="Número máximo de resultados")
    include_snippets: Optional[bool] = Field(False, description="Incluir fragmentos de texto")
    mode: Optional[str] = Field("literal", description="Modo de búsqueda: 'literal' o 'semantic'")

class SearchResult(BaseModel):
    """
    Resultado de búsqueda: incluye id, score, snippet y metadatos.
    """
    id: str
    score: float
    snippet: Optional[str] = None
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

@router.post("/search", response_model=Dict[str, Any])
async def search_endpoint(request: SearchRequest = Body(...)):
    """
    Endpoint de búsqueda de versículos.
    Permite búsqueda literal o semántica sobre el corpus, con filtros y paginación.
    - q: consulta de texto
    - filters: filtros opcionales
    - top_k: número máximo de resultados
    - include_snippets: incluir fragmentos de texto
    - mode: 'literal' o 'semantic'
    Responde con lista de resultados y embedding de la consulta si aplica.
    """
    results = await search_usecase.search(
        request.q,
        top_k=request.top_k or 10,
        mode=request.mode or "literal"
    )
    return SearchResponse(results=[SearchResult(**r) for r in results], query_embedding=None)


class EmbeddingUpsertItem(BaseModel):
    """
    Item para upsert de embeddings en Pinecone.
    El campo id es obligatorio y debe seguir el patrón de referencia.
    """
    id: str
    text: str
    metadata: Optional[Dict[str, Any]] = None

class EmbeddingUpsertRequest(BaseModel):
    """
    Request para upsert de embeddings: lista de items y namespace opcional.
    """
    items: List[EmbeddingUpsertItem]
    namespace: Optional[str] = None

class EmbeddingUpsertResponse(BaseModel):
    """
    Respuesta de upsert: cantidad de upserted y lista de fallos.
    """
    upserted: int
    failed: List[Dict[str, Any]]


@router.post("/embeddings/upsert", response_model=EmbeddingUpsertResponse)
async def embeddings_upsert_endpoint(request: EmbeddingUpsertRequest):
    """
    Upsert de embeddings en Pinecone.
    Genera embedding con Ollama y almacena en el vector DB.
    - items: lista de objetos con id, text y metadata
    - namespace: opcional
    Responde con cantidad de upserted y lista de fallos.
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
    """
    Documento completo: id, texto, metadatos y fechas.
    """
    id: str
    text: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str

@router.get("/documents/{id}", response_model=DocumentResponse)
async def get_document_by_id(id: str):
    """
    Devuelve el documento por ID, usando el corpus local como fuente inicial.
    - id: identificador único del documento (patrón AT/NT-volumen-capitulo-versiculo)
    Responde con el documento completo y fechas.
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


class DocumentListResponse(BaseModel):
    """
    Respuesta de listado de documentos con paginación.
    """
    items: List[DocumentResponse]
    total: int
    limit: int
    offset: int

@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    """
    Lista documentos del corpus local con paginación básica.
    - limit: máximo de documentos por página
    - offset: desplazamiento inicial
    Responde con lista de documentos y total.
    """
    import json
    import os
    from datetime import timezone
    corpus_path = os.path.join(os.path.dirname(__file__), '../../versiculos.jsonl')
    items = []
    try:
        with open(corpus_path, encoding='utf-8') as f:
            for idx, line in enumerate(f):
                if idx < offset:
                    continue
                if len(items) >= limit:
                    break
                doc = json.loads(line)
                now = doc.get('updated_at') or doc.get('created_at') or datetime.now(timezone.utc).isoformat()
                items.append(DocumentResponse(
                    id=doc['id'],
                    text=doc['text'],
                    metadata=doc.get('metadata', {}),
                    created_at=doc.get('created_at', now),
                    updated_at=doc.get('updated_at', now)
                ))
        # Calcular total recorriendo todo el archivo
        with open(corpus_path, encoding='utf-8') as f:
            total = sum(1 for _ in f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo corpus: {str(e)}")
    return DocumentListResponse(items=items, total=total, limit=limit, offset=offset)


class ReindexRequest(BaseModel):
    """
    Request para reindexado: batch_size y dry_run opcionales.
    """
    batch_size: Optional[int] = 1000
    dry_run: Optional[bool] = False

class ReindexResponse(BaseModel):
    """
    Respuesta de reindex: job_id y status.
    """
    job_id: str
    status: str

@router.post("/admin/reindex", response_model=ReindexResponse)
async def admin_reindex_endpoint(request: ReindexRequest):
    """
    Lanza un job background para reconciliar/repoblar vector DB.
    - batch_size: tamaño de lote
    - dry_run: si es True, solo simula
    Responde con job_id y status ('accepted' o 'dry_run').
    """
    job_id = str(uuid.uuid4())
    # Simulación: en producción, aquí se lanzaría el job real (Celery, arq, etc.)
    if not request.dry_run:
        # Aquí iría la lógica para lanzar el job real de reindex
        # Por ahora, solo se registra el job_id y status
        status = "accepted"
    else:
        status = "dry_run"
    return ReindexResponse(job_id=job_id, status=status)


class DocumentCreateRequest(BaseModel):
    """
    Request para crear o actualizar documento.
    El campo id es obligatorio y debe seguir el patrón de referencia.
    """
    id: str
    text: str
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def validate_id(cls, v: str) -> str:
        """
        Valida que el id cumpla el patrón AT/NT-volumen-capitulo-versiculo (ej: AT-genesis-06-010).
        """
        pattern = r"^(AT|NT)-[a-z0-9\-]+-\d{2}-\d{3}$"
        if not re.match(pattern, v):
            raise ValueError("El id no cumple el patrón requerido (ej: AT-genesis-06-010)")
        return v

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_id

class DocumentCreateResponse(BaseModel):
    """
    Respuesta de creación/actualización de documento.
    """
    id: str
    status: str  # "created" | "updated"

@router.post("/documents", response_model=DocumentCreateResponse)
async def create_or_update_document(request: DocumentCreateRequest = Body(...)):
    """
    Crea o actualiza un documento en el corpus local (versiculos.jsonl).
    - id: obligatorio, patrón AT/NT-volumen-capitulo-versiculo
    - text: texto completo del versículo
    - metadata: metadatos opcionales
    Responde con id y estado ('created' o 'updated').
    """
    import json
    import os
    from datetime import timezone
    corpus_path = os.path.join(os.path.dirname(__file__), '../../versiculos.jsonl')
    doc_id = request.id or str(abs(hash(request.text + str(request.metadata or {}))))
    now = datetime.now(timezone.utc).isoformat()
    new_doc = {
        "id": doc_id,
        "text": request.text,
        "metadata": request.metadata or {},
        "created_at": now,
        "updated_at": now
    }
    # Leer todos los documentos y buscar si existe
    docs = []
    updated = False
    try:
        if os.path.exists(corpus_path):
            with open(corpus_path, encoding='utf-8') as f:
                for line in f:
                    doc = json.loads(line)
                    if doc.get('id') == doc_id:
                        # Actualizar documento
                        doc.update(new_doc)
                        updated = True
                    docs.append(doc)
        # Si no existe, agregar nuevo
        if not updated:
            docs.append(new_doc)
        # Sobrescribir el archivo
        with open(corpus_path, 'w', encoding='utf-8') as f:
            for doc in docs:
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error escribiendo corpus: {str(e)}")
    return DocumentCreateResponse(id=doc_id, status="updated" if updated else "created")
