from fastapi import FastAPI
from src.api.search import router as search_router

app = FastAPI(title="apicone", version="0.1.0")

app.include_router(search_router)

@app.get("/health")
def health():
    return {"status": "ok"}
