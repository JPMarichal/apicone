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
4. Accede a la documentación interactiva (OpenAPI/Swagger UI) en [http://localhost:8000/docs](http://localhost:8000/docs).
   - Aquí puedes explorar, probar y visualizar todos los endpoints, modelos y contratos de la API.
   - También puedes copiar los ejemplos de payload y respuestas para usarlos en Postman o cualquier cliente HTTP.

## Acceso y pruebas con Postman

## Especificación OpenAPI para clientes

La especificación OpenAPI completa está disponible en formato JSON en:

- [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

Puedes descargar este archivo y usarlo para:
- Generar SDKs o clientes automáticos en cualquier lenguaje (usando herramientas como Swagger Codegen, OpenAPI Generator, etc).
- Importar todos los endpoints y modelos en Postman, Insomnia, o cualquier cliente compatible.
- Validar contratos y documentar integraciones con otros sistemas.

**Ejemplo para descargar la especificación:**

```sh
curl -O http://localhost:8000/openapi.json
```

Puedes importar los endpoints manualmente o desde la especificación OpenAPI:

1. Abre Postman y crea una nueva colección.
2. Para cada endpoint, usa la URL base `http://localhost:8000` y el path correspondiente (ejemplo: `/api/v1/search`).
3. Selecciona el método adecuado (GET, POST, etc) y copia el payload de ejemplo desde la documentación interactiva (`/docs`).
4. Para endpoints POST, selecciona "Body" → "raw" → "JSON" e ingresa el JSON de ejemplo.
5. Envía la petición y revisa la respuesta.

**Tip:** Puedes importar la especificación OpenAPI directamente en Postman:
   - Ve a "Import" → "Link" y pega `http://localhost:8000/openapi.json`.
   - Postman generará automáticamente todos los endpoints y ejemplos listos para probar.

**Ejemplo de petición POST en Postman:**

```
POST http://localhost:8000/api/v1/search
Body (raw, JSON):
{
  "q": "amor",
  "top_k": 3,
  "mode": "literal"
}
```

**Ejemplo de petición GET en Postman:**

```
GET http://localhost:8000/api/v1/documents/NT-2-juan-01-006
```

**Ejemplo de petición POST para reindexado:**

```
POST http://localhost:8000/api/v1/admin/reindex
Body (raw, JSON):
{
  "batch_size": 100,
  "dry_run": false
}
```

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
