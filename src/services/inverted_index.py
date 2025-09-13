import os
import orjson
import unicodedata
import re
from typing import Dict, Set, List
from pathlib import Path

class InvertedIndexService:
    """
    Servicio para gestionar el índice inverso, con carga desde disco y serialización optimizada.
    Aplica normalización y tokenización eficiente.
    """
    def __init__(self, jsonl_path: str, index_path: str = None):
        self.jsonl_path = jsonl_path
        self.index_path = index_path or jsonl_path + ".idx"
        self.text_by_id: Dict[str, str] = {}
        self.ref_by_id: Dict[str, str] = {}
        self.normwords_by_id: Dict[str, str] = {}
        self.postings: Dict[str, Set[str]] = {}
        self._load_or_build_index()

    def _load_or_build_index(self):
        if Path(self.index_path).exists():
            self._load_index()
        else:
            self._build_index()
            self._save_index()

    def _build_index(self):
        self.postings = {}
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                o = orjson.loads(line)
                vid = o["id"]
                ref = (o.get("metadata") or {}).get("reference") or o.get("Referencia") or ""
                txt = o.get("text") or o.get("Contenido") or ""
                self.text_by_id[vid] = txt
                self.ref_by_id[vid] = ref
                blob_words = self.norm_words(ref + " " + txt)
                self.normwords_by_id[vid] = blob_words
                for t in self.tokenize_words(blob_words):
                    self.postings.setdefault(t, set()).add(vid)

    def _save_index(self):
        data = {
            "text_by_id": self.text_by_id,
            "ref_by_id": self.ref_by_id,
            "normwords_by_id": self.normwords_by_id,
            "postings": {k: list(v) for k, v in self.postings.items()}
        }
        with open(self.index_path, "wb") as f:
            f.write(orjson.dumps(data))

    def _load_index(self):
        with open(self.index_path, "rb") as f:
            data = orjson.loads(f.read())
        self.text_by_id = data["text_by_id"]
        self.ref_by_id = data["ref_by_id"]
        self.normwords_by_id = data["normwords_by_id"]
        self.postings = {k: set(v) for k, v in data["postings"].items()}

    @staticmethod
    def norm_basic(s: str) -> str:
        s = s.lower()
        s = unicodedata.normalize("NFD", s)
        return "".join(c for c in s if unicodedata.category(c) != "Mn")

    @staticmethod
    def norm_words(s: str) -> str:
        s = InvertedIndexService.norm_basic(s)
        s = re.sub(r"[^a-z0-9]+", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    @staticmethod
    def tokenize_words(s: str) -> List[str]:
        return re.findall(r"[a-z0-9]+", InvertedIndexService.norm_words(s))

    # Métodos de consulta pueden agregarse aquí
