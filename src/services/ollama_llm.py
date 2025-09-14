import httpx
import os
import logging
import traceback
from typing import List, Dict, Any

from typing import Optional

logger = logging.getLogger(__name__)


class OllamaLLMValidator:
    # Logear la ruta del módulo para depuración de carga
    logger.warning("ollama_llm module loaded from: %s", __file__)
    """
    Valida la relevancia semántica de los resultados usando el LLM de Ollama.
    """
    def __init__(self, base_url: Optional[str] = None, model: str = "llama3"):
        self.base_url = base_url or os.getenv("OLLAMA_LLM_URL", "http://ollama:11434/api/generate")
        self.model = model

    async def validate_results(self, query: str, results: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        # Defensive: aceptar kwargs inesperadas (p.ej. batch_size) y loguear su origen para depuración
        if kwargs:
            # Loguear advertencia con la pila de llamadas para localizar el caller
            logger.warning("validate_results received unexpected kwargs: %s", kwargs)
            tb = "\n".join(traceback.format_stack())
            logger.debug("Call stack for unexpected kwargs in validate_results:\n%s", tb)

        # Construye el prompt para el LLM
        prompt = self._build_prompt(query, results)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.base_url,
                json={"model": self.model, "prompt": prompt}
            )
            response.raise_for_status()
            data = response.json()
            # Espera una lista de índices válidos en la respuesta
            valid_indices = self._parse_llm_response(data)
            return [results[i] for i in valid_indices if i < len(results)]

    def _build_prompt(self, query: str, results: List[Dict[str, Any]]) -> str:
        # Presenta la pregunta y los resultados al LLM
        prompt = f"Pregunta: {query}\n\nResultados:\n"
        for i, r in enumerate(results):
            ref = r.get("ref") or r.get("metadata", {}).get("ref", "")
            snippet = r.get("snippet", "")
            prompt += f"[{i}] {ref}: {snippet}\n"
        prompt += ("\nIndica los índices de los resultados que realmente responden a la pregunta, "
                   "excluyendo los irrelevantes. Devuelve una lista de índices válidos, por ejemplo: [0,2,5]\n")
        return prompt

    def _parse_llm_response(self, data: Dict[str, Any]) -> List[int]:
        # Extrae la lista de índices válidos del output del LLM
        import re
        output = data.get("response", "")
        match = re.search(r"\[(.*?)\]", output)
        if match:
            indices = match.group(1)
            return [int(i) for i in indices.split(",") if i.strip().isdigit()]
        return []
