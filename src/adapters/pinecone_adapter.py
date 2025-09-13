from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional

class PineconeAdapter:
    def __init__(self, api_key: str, environment: str, index_name: str, namespace: Optional[str] = None):
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index(index_name)
        self.namespace = namespace

    def query(self, embedding: List[float], top_k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        res = self.index.query(
            vector=embedding,
            top_k=top_k,
            namespace=self.namespace,
            filter=filter or {},
            include_metadata=True
        )
        matches = res.get("matches", [])
        out = []
        for m in matches:
            md = m.get("metadata", {}) or {}
            out.append({
                "id": m.get("id"),
                "ref": md.get("reference") or md.get("Referencia") or "",
                "snippet": md.get("contenido") or "",
                "score": m.get("score", 0.0),
                "metadata": md
            })
        return out
