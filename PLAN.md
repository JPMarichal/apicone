# Plan de trabajo — apicone

Este documento recoge el diseño y plan de trabajo inicial para convertir `apicone` en una API de backend independiente, modular y alineada con principios SOLID y arquitectura limpia.

## Objetivo
Crear una API independiente que exponga búsqueda por embeddings, gestión de documentos y operaciones administrativas (reindex, upsert), desacoplada del resto de la solución, testeable y fácilmente desplegable (Docker/K8s). El sistema debe permitir búsquedas literales y semánticas sobre un corpus de versículos bíblicos, indexados tanto localmente como en Pinecone.

## Resumen del stack recomendado
- Lenguaje: Python 3.11+
- Framework web: FastAPI (ASGI, validación con Pydantic, OpenAPI automático)
- Server production: Uvicorn (workers) / Gunicorn + Uvicorn workers
- Vector DB: Pinecone (adapter con interfaz para poder cambiar por Milvus / Weaviate)
- Metadatos y persistencia: PostgreSQL (asyncpg + SQLAlchemy async / o SQLModel)
- Cache / cola ligera: Redis
- Background jobs: Celery (con Redis) o alternativa async (arq) si se prefiere todo asyncio
- Observabilidad: logging estructurado, Sentry, Prometheus + Grafana
- Testing: pytest, httpx, pytest-asyncio
- Lint/format: ruff, black, isort, mypy
- Contenerización: Docker + docker-compose (dev); K8s (prod opcional)

> El archivo `versiculos.jsonl` contiene más de 42,000 registros, cada uno con los campos principales: `id`, `text` (texto completo del versículo) y `metadata` (referencia, libro, capítulo, versículo, idioma, etc.). En Pinecone se indexan los versículos, usando el campo `contenido` en `metadata` para exponer el texto completo. La diferencia de registros entre ambos sistemas se ignora por ahora, ya que no afecta la funcionalidad principal.

> El archivo `.env` en la raíz contiene la clave de acceso para Pinecone (`PINECONE_API_KEY`).

## Principios de diseño y SOLID aplicados
- Single Responsibility: capas bien separadas — routers, controllers, use-cases, repositories/adapters.
- Open/Closed: repositorios y servicios definidos por interfaces; nuevas implementaciones se añaden sin tocar la lógica de negocio.
- Liskov Substitution: adapters cumplen contratos/Protocol y son intercambiables.
- Interface Segregation: interfaces pequeñas (SearchRepository, VectorRepository, MetadataRepository).
- Dependency Inversion: use-cases dependen de abstracciones, no de implementaciones concretas.

## Arquitectura por capas (sugerida)
- src/apicone/main.py — app factory (FastAPI)
- src/apicone/api/ — routers y esquemas (Pydantic)
- src/apicone/controllers/ — adaptadores request -> usecase
- src/apicone/usecases/ — lógica de dominio orquestada
- src/apicone/domain/ — entidades y value objects
- src/apicone/repositories/ — interfaces/ports
- src/apicone/adapters/ — implementaciones concretas (pinecone_adapter, postgres_adapter, redis_adapter)
- src/apicone/services/ — embedder, text-chunker, dedup
- src/apicone/infra/ — db sessions, DI, logging, metrics
- src/apicone/tasks/ — worker/Celery tasks
- tests/ — unit & integration

## Contrato API inicial (v1)
Base path: `/api/v1`

1) GET /health
- Response: { "status": "ok", "uptime": <s>, "components": { "db": "ok", "pinecone": "ok" } }

2) POST /api/v1/search
- Body: { "q": string, "filters"?: object, "top_k"?: int = 10, "include_snippets"?: bool }
- Response: { "results": [ { "id": str, "score": float, "snippet"?: str, "metadata": object } ], "query_embedding"?: [float] }
- Errors: 400, 401, 429, 503

3) POST /api/v1/embeddings/upsert
- Body: { "items": [ { "id"?: str, "text": str, "metadata"?: object } ], "namespace"?: str }
- Response: { "upserted": int, "failed": [ { "id"?, "reason" } ] }
- Nota: los ids pueden ser generados por cliente o por servidor (hash para idempotencia)

4) GET /api/v1/documents/{id}
- Response: { "id": str, "text": str, "metadata": object, "created_at": ISO, "updated_at": ISO }

5) POST /api/v1/documents
- Body: { "id"?: str, "text": str, "metadata"?: object }
- Response: { "id": str, "status": "created" | "updated" }

6) POST /api/v1/admin/reindex (protegido)
- Body: { "batch_size"?: int, "dry_run"?: bool }
- Response: { "job_id": str, "status": "accepted" }
- Acción: lanza un job background para reconciliar/repoblar vector DB

Autenticación: JWT (OAuth2 password/client_credentials) y/o API keys para servicios. Rate limiting por API key.

## Formas de datos (ejemplo)
- DocumentDTO:
  - id: str
  - text: str
  - metadata: dict (volumen, libro_id, capitulo, versiculo, pericopa_id...)

- SearchResult:
  - id: str
  - score: float
  - snippet: str
  - metadata: dict

## Consideraciones técnicas
- Chunking: textos largos se fragmentan y se almacenan con metadata de chunk (offsets) y parent_id.
- Duplicados: idempotencia por id o hash(text+metadata). Detectar y eliminar duplicados en pipeline.
- Timeouts y retries: envoltura con backoff para llamadas a Pinecone y DB; circuit breaker para degradado.
- Consistencia: jobs de reconciliación (reindex) y auditoría para detectar mismatch entre metadata DB y vector DB.
- Escalabilidad: API stateless, background workers stateful (cola Redis). Escalado horizontal mediante contenedores.
- El índice inverso se construye localmente a partir de `versiculos.jsonl`, aprovechando tanto el texto como la referencia y metadatos para búsquedas literales y semánticas. La búsqueda semántica utiliza embeddings generados por Ollama y consulta Pinecone, mostrando resultados ordenados por score o por orden canónico.

## Observabilidad y calidad
- Logs JSON estructurado; Sentry para errores críticos.
- Métricas Prometheus (latencias, rates, counts); dashboards en Grafana.
- CI: GitHub Actions — pasos: lint, mypy, tests, build image.
- Seguridad: no incluir secrets en repo; usar vault/secret manager.

## Requisitos de aceptación mínimos (MVP)
- Endpoints /health, /search, /embeddings/upsert implementados y documentados.
- Adapter a Pinecone funcional (con mocking en tests).
- Tests unitarios para use-cases; integración básica con DB emulada/mocked.
- Dockerfile y docker-compose para dev con Postgres + Redis.

## Roadmap corto (4 sprints pequeño)
1. Diseño y análisis:
   - Confirmar stack y contrato API. (Artefacto: `PLAN.md`, contrato OpenAPI inicial)
   - Analizar la lógica de `ask_pinecone.py` y definir los endpoints equivalentes y mejorados.
2. Scaffold y entorno:
   - Crear repo `apicone` con FastAPI app, healthcheck, configuración y Dockerfile.
   - Definir y probar el stack completo en Docker Compose (API, Postgres, Redis).
   - Configurar variables de entorno y documentación básica.
3. Migración y desarrollo de lógica de negocio:
   - Migrar la lógica principal de `ask_pinecone.py` a la API (búsqueda literal y semántica).
   - Implementar los endpoints principales: `/search`, `/embeddings/upsert`, `/health`, etc.
   - Adaptar y optimizar el índice inverso y la integración con Pinecone.
   - Validar que la API cubra todos los modos de consulta y sugerencias del script original.
   - Crear y ejecutar pruebas unitarias y de integración para los endpoints.
   - Documentar los endpoints en el código (docstrings y modelos Pydantic).
4. Despliegue y documentación avanzada:
   - Exponer la documentación OpenAPI y endpoints interactivos.
   - Probar el rendimiento en Docker (Windows y Ubuntu).
   - Desplegar en VPS Ubuntu y validar funcionamiento.
   - Ampliar la documentación para usuarios y desarrolladores.

## Tareas inmediatas (fase 3)
- [ ] Migrar la lógica principal de `ask_pinecone.py` a FastAPI, implementando búsqueda literal y semántica.
- [ ] Implementar los endpoints principales definidos en el contrato.
- [ ] Optimizar el índice inverso y la integración con Pinecone.
- [ ] Validar cobertura funcional y sugerencias equivalentes al script original.
- [ ] Crear y ejecutar pruebas unitarias y de integración.
- [ ] Documentar los endpoints y modelos en el código.

## Estimación y recursos
- ETA para MVP básico (scaffold + /search + /upsert + tests): 1–2 semanas (1 dev full-time) dependiendo de acceso a Pinecone y datos de ejemplo.

## Notas finales
- Diseñar interfaces (Protocols) para todos los adaptadores desde el principio. Esto hará la base de la abstracción y permitirá cambiar componentes sin cambios en la lógica de negocio.
- Mantener casos de uso puros y fácilmente testeables (sin dependencias de FastAPI dentro de usecases).

> La API estará expuesta a clientes que requieren documentación OpenAPI para su consumo. FastAPI genera y expone automáticamente la documentación interactiva en `/docs` (Swagger UI), `/redoc` (Redoc) y el esquema OpenAPI en `/openapi.json`. Esto facilita la integración y el desarrollo de clientes, permitiendo la descarga y consulta directa del contrato OpenAPI actualizado.

Actualiza este archivo según acuerdos y confirmaciones; cuando confirmes el stack, procedo a generar el scaffold inicial y el contrato OpenAPI en `apicone`.

## Plan de trabajo detallado para desarrollo y despliegue

### Fase 1: Preparación del entorno y repositorio
- Crear el repositorio en GitHub (`apicone`).
- Clonar el repositorio en la laptop de desarrollo (Windows 11).
- Configurar `.gitignore` y archivos base (`README.md`, `PLAN.md`).
- Crear y complementar el archivo `.env` con las variables necesarias.

### Fase 2: Scaffold y stack de desarrollo
- Generar la estructura de carpetas y archivos principales (`src/`, `tests/`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`).
- Incluir configuración para FastAPI, Pinecone, Postgres y Redis en `docker-compose.yml`.
- Probar el stack completo con Docker Compose en modo detached (`docker-compose up -d`).
- Validar que los servicios (API, Postgres, Redis) se levantan correctamente.
- Documentar la estructura y dependencias en el README.

### Fase 3: Migración y desarrollo de lógica de negocio
- Migrar la lógica principal de `ask_pinecone.py` a la API (búsqueda literal y semántica).
- Implementar los endpoints principales: `/search`, `/embeddings/upsert`, `/health`, etc.
- Adaptar y optimizar el índice inverso y la integración con Pinecone.
- Validar que la API cubra todos los modos de consulta y sugerencias del script original.
- Crear y ejecutar pruebas unitarias y de integración para los endpoints.
- Documentar los endpoints en el código (docstrings y modelos Pydantic).

### Fase 4: Integración continua, despliegue y documentación avanzada
- Configurar GitHub Actions para CI/CD (lint, tests, build de imagen Docker).
- Añadir workflow para publicar la imagen en GitHub Container Registry o Docker Hub.
- Desplegar en VPS Ubuntu y validar funcionamiento.
- Exponer la documentación OpenAPI y endpoints interactivos.
- Ampliar la documentación para usuarios y desarrolladores.

---

Este plan asegura portabilidad, reproducibilidad y facilidad de despliegue entre entornos Windows y Linux, integrando buenas prácticas de CI/CD y contenedores.

## Contexto de desarrollo
- El directorio de trabajo local en la laptop de desarrollo (Jarvis) es `D:/myapps/apicone`.
- El MVP debe emular y mejorar el comportamiento del script `ask_pinecone.py`, convirtiendo su lógica en una API accesible vía HTTP, con endpoints equivalentes y mejoras en la estructura, rendimiento y documentación.
