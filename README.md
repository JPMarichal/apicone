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

## Roadmap
Consulta el archivo `PLAN.md` para ver el diseño, tareas y avances.

## Licencia
MIT
