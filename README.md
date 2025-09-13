# apicone

API de consulta semántica y literal de escrituras, basada en Pinecone y FastAPI.

## Descripción
Este proyecto expone una API que permite realizar búsquedas literales y semánticas sobre un corpus de versículos bíblicos, utilizando Pinecone como base vectorial y FastAPI como framework web. El objetivo inicial (MVP) es emular y mejorar el comportamiento del script `ask_pinecone.py`, convirtiéndolo en una API moderna y portable.

## Características principales
- Búsqueda literal y semántica de versículos.
- Endpoints REST documentados con OpenAPI (Swagger UI).
- Integración con Pinecone, Postgres y Redis.
- Despliegue portable con Docker y docker-compose.
- Optimización de índices inversos y rendimiento.
- CI/CD con GitHub Actions.

## Estructura del proyecto
```
├── src/           # Código fuente principal (FastAPI, lógica de negocio)
├── tests/         # Pruebas unitarias y de integración
├── Dockerfile     # Imagen de la API
├── docker-compose.yml # Orquestación de servicios
├── PLAN.md        # Documento de diseño y roadmap
├── .env.example   # Variables de entorno de ejemplo
├── .gitignore     # Exclusiones de git
└── README.md      # Este archivo
```

## Requisitos
- Python 3.11+
- Docker y Docker Compose
- Acceso a Pinecone (API Key)

## Uso rápido
1. Clona el repositorio:
   ```sh
   git clone https://github.com/jpmarichal/apicone.git
   cd apicone
   ```
2. Copia y edita `.env.example` como `.env` con tus claves.
3. Levanta el entorno de desarrollo:
   ```sh
   docker-compose up --build
   ```
4. Accede a la documentación interactiva en [http://localhost:8000/docs](http://localhost:8000/docs)

## Endpoints principales

### `/api/v1/search` (POST)
Busca versículos por texto, modo literal o semántico.
- **Body:**
  - `q`: consulta de texto
  - `filters`: filtros opcionales
  - `top_k`: máximo de resultados
  - `include_snippets`: incluir fragmentos
  - `mode`: 'literal' o 'semantic'
- **Response:**
  - `results`: lista de resultados (id, score, snippet, metadata)
  - `query_embedding`: embedding de la consulta (si aplica)

### `/api/v1/embeddings/upsert` (POST)
Upsert de embeddings en Pinecone.
- **Body:**
  - `items`: lista de objetos `{id, text, metadata}`
  - `namespace`: opcional
- **Response:**
  - `upserted`: cantidad de embeddings insertados
  - `failed`: lista de fallos

### `/api/v1/documents/{id}` (GET)
Obtiene un documento por ID.
- **Response:**
  - `id`, `text`, `metadata`, `created_at`, `updated_at`

### `/api/v1/documents` (GET)
Lista documentos con paginación.
- **Query params:**
  - `limit`, `offset`
- **Response:**
  - `items`: lista de documentos
  - `total`, `limit`, `offset`

### `/api/v1/documents` (POST)
Crea o actualiza un documento en el corpus local.
- **Body:**
  - `id`: obligatorio, patrón AT/NT-volumen-capitulo-versiculo
  - `text`: texto completo
  - `metadata`: opcional
- **Response:**
  - `id`, `status`: 'created' o 'updated'

### `/api/v1/admin/reindex` (POST)
Lanza un job de reindexado en background.
- **Body:**
  - `batch_size`: tamaño de lote
  - `dry_run`: simula si es True
- **Response:**
  - `job_id`, `status`: 'accepted' o 'dry_run'

## Modelos principales
- `SearchRequest`, `SearchResult`
- `EmbeddingUpsertItem`, `EmbeddingUpsertRequest`, `EmbeddingUpsertResponse`
- `DocumentResponse`, `DocumentListResponse`, `DocumentCreateRequest`, `DocumentCreateResponse`
- `ReindexRequest`, `ReindexResponse`

## Notas
- El campo `id` de los documentos y embeddings debe seguir el patrón: `AT|NT-libro-capitulo-versiculo` (ej: `AT-genesis-06-010`).
- El corpus local se actualiza en cada creación/actualización vía API.
- Todos los endpoints están documentados y testeados.

## Roadmap
Consulta el archivo `PLAN.md` para ver el diseño, tareas y avances.

## Licencia
MIT
