# ask_pinecone.py
import os
import re
import json
import unicodedata
import difflib
from collections import defaultdict
from typing import List, Dict, Set

import ollama
from pinecone import Pinecone

INDEX_NAME = "escrituras"
NAMESPACE  = "es"
JSONL_FILE = "versiculos.jsonl"   # base para índice literal (id -> texto / ref)
ORDER_MODE = os.getenv("ASK_ORDER", "canon").lower().strip()  # "canon" (default) o "score"

# =============== utilidades ===============
def clear_screen():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        print("\033c", end="")

def norm_basic(s: str) -> str:
    """minúsculas + sin tildes (conserva guiones para otros usos)"""
    s = s.lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def norm_words(s: str) -> str:
    """
    Normaliza para coincidencia por palabra:
    - minúsculas, sin tildes
    - reemplaza todo lo no [a-z0-9] por espacio (elimina guiones/puntuación)
    - colapsa espacios
    """
    s = norm_basic(s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def tokenize_words(s: str) -> List[str]:
    """Tokens a-z0-9 ya normalizados (palabra completa)."""
    return re.findall(r"[a-z0-9]+", norm_words(s))

def extract_phrases_and_tokens(q: str):
    # Frases entre comillas ("...") / (‘...’ / “...”)
    phrases = re.findall(r'"([^"]+)"|“([^”]+)”|\'([^\']+)\'', q)
    phrases = ["".join(p).strip() for p in phrases if "".join(p).strip()]
    # Tokens candidatos (palabras con letras/guion)
    raw_tokens = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9\-]+", q)
    # filtra tokens muy cortos / stopwords básicas
    stop = {"quien","que","donde","de","la","el","los","las","un","una","y","en","del","al","es","son","se"}
    tokens = []
    for t in raw_tokens:
        tb = norm_basic(t)
        if len(tb) >= 3 and tb not in stop:
            tokens.append(t)
    return phrases, tokens

# =============== orden canónico ===============
_CANON_ORDER = [
    # AT
    "Génesis","Éxodo","Levítico","Números","Deuteronomio","Josué","Jueces","Rut",
    "1 Samuel","2 Samuel","1 Reyes","2 Reyes","1 Crónicas","2 Crónicas","Esdras","Nehemías","Ester",
    "Job","Salmos","Proverbios","Eclesiastés","Cantares","Isaías","Jeremías","Lamentaciones",
    "Ezequiel","Daniel","Oseas","Joel","Amós","Abdías","Jonás","Miqueas","Nahúm","Habacuc",
    "Sofonías","Hageo","Zacarías","Malaquías",
    # NT
    "Mateo","Marcos","Lucas","Juan","Hechos","Romanos","1 Corintios","2 Corintios","Gálatas",
    "Efesios","Filipenses","Colosenses","1 Tesalonicenses","2 Tesalonicenses","1 Timoteo",
    "2 Timoteo","Tito","Filemón","Hebreos","Santiago","1 Pedro","2 Pedro","1 Juan","2 Juan",
    "3 Juan","Judas","Apocalipsis",
    # BoM
    "1 Nefi","2 Nefi","Jacob","Enós","Jarom","Omni","Palabras de Mormón","Mosíah","Alma",
    "Helamán","3 Nefi","4 Nefi","Mormón","Éter","Moroni",
    # DyC
    "Doctrina y Convenios",
    # PGP
    "Moisés","Abraham","José Smith—Mateo","José Smith—Historia","Artículos de Fe"
]
_ALIAS = {
    # equivalencias ortográficas/diacríticas de libros (no de términos)
    "genesis":"génesis","exodo":"éxodo","levitico":"levítico","numeros":"números",
    "nehemias":"nehemías","eclesiastes":"eclesiastés","amos":"amós","jonas":"jonás",
    "nahum":"nahúm","galatas":"gálatas","filemon":"filemón","enos":"enós",
    "mosiah":"mosíah","helaman":"helamán","mormon":"mormón","eter":"éter",
    "moises":"moisés",
    # variantes de JS—Mateo/Historia y DyC
    "jose smith-mateo":"josé smith—mateo","jose smith—mateo":"josé smith—mateo",
    "jose smith-historia":"josé smith—historia","jose smith—historia":"josé smith—historia",
    "dyc":"doctrina y convenios","articulos de fe":"artículos de fe",
    "cantar de los cantares":"cantares"
}
def _norm_book_key(s: str) -> str:
    s = s.replace("—","-").replace("–","-")
    s = norm_basic(s)
    return re.sub(r"\s+", " ", s).strip()
_BOOK_INDEX: Dict[str,int] = {}
for i,name in enumerate(_CANON_ORDER):
    _BOOK_INDEX[_norm_book_key(name)] = i
for a,t in _ALIAS.items():
    _BOOK_INDEX[_norm_book_key(a)] = _BOOK_INDEX.get(_norm_book_key(t), len(_CANON_ORDER)+999)

def parse_reference(ref: str):
    m = re.match(r"^(?P<book>.+?)\s+(?P<chap>\d+)(?::(?P<verse>\d+))?$", ref.strip())
    if not m: return ref, 0, 0
    book = m.group("book").strip()
    chap = int(m.group("chap"))
    verse = int(m.group("verse") or 0)
    return book, chap, verse

def canon_sort_key(ref: str):
    book, chap, verse = parse_reference(ref)
    order = _BOOK_INDEX.get(_norm_book_key(book), len(_CANON_ORDER)+1000)
    return (order, chap, verse)

# =============== índice literal (RAM) ===============
TEXT_BY_ID: Dict[str,str] = {}
REF_BY_ID: Dict[str,str]  = {}
NORMWORDS_BY_ID: Dict[str,str] = {}
POSTINGS: Dict[str, Set[str]] = defaultdict(set)  # token -> set(ids)

def _add_hyphen_collapses(src_text: str) -> List[str]:
    """Detecta palabras con guion en la versión sin tildes y añade su forma 'pegada' (bet-el -> betel)."""
    base = norm_basic(src_text)
    hyphen_words = re.findall(r"\b([a-z0-9]+-[a-z0-9]+)\b", base)
    collapsed = [w.replace("-", "") for w in hyphen_words]
    return collapsed

def build_inverted_index(jsonl_path: str = JSONL_FILE):
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line: continue
                o = json.loads(line)
                vid = o["id"]
                # texto/ref desde JSONL (o metadata si estuviera presente)
                ref = (o.get("metadata") or {}).get("reference") or o.get("Referencia") or ""
                txt = o.get("text") or o.get("Contenido") or ""
                TEXT_BY_ID[vid] = txt
                REF_BY_ID[vid]  = ref
                # normalizado para búsqueda literal
                blob_words = norm_words(ref + " " + txt)
                NORMWORDS_BY_ID[vid] = blob_words
                # tokens principales
                for t in tokenize_words(blob_words):
                    POSTINGS[t].add(vid)
                # y colapsos de guion a un solo token (Bet-el -> betel)
                for extra in _add_hyphen_collapses(ref + " " + txt):
                    POSTINGS[extra].add(vid)
    except FileNotFoundError:
        # si no está el JSONL, el literal total no estará disponible;
        # seguiremos pudiendo hacer búsqueda semántica
        pass

build_inverted_index()

# =============== capa semántica (Pinecone) ===============
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index(INDEX_NAME)

def pinecone_semantic_candidates(query: str, top_k: int, sample_k: int):
    emb = ollama.embed(model="nomic-embed-text", input=query)["embeddings"][0]
    res = index.query(vector=emb, top_k=sample_k, namespace=NAMESPACE, include_metadata=True)
    matches = res.get("matches", [])
    # keep structure uniform
    out = []
    for m in matches:
        md = m.get("metadata", {}) or {}
        out.append({
            "id": m.get("id"),
            "ref": md.get("reference") or md.get("Referencia") or "",
            "texto": md.get("contenido") or TEXT_BY_ID.get(m.get("id"), "") or "",
            "score": m.get("score", 0.0)
        })
    return out

# =============== lógica literal/mixta ===============
def ids_for_phrase(phrase: str) -> Set[str]:
    """
    Candidatos por frase:
    1) Intersección por tokens (rápido)
    2) Refinamiento: la frase completa debe aparecer como palabra a palabra en NORMWORDS.
    Si la intersección queda vacía, hacemos un escaneo lineal (42k OK).
    """
    phrase_norm = norm_words(phrase)
    toks = tokenize_words(phrase_norm)
    if not toks:
        return set()
    # intersección por postings
    sets = [POSTINGS.get(t, set()) for t in toks]
    if not sets:
        return set()
    cand = set.intersection(*sets) if all(sets) else set()
    # si no hay, escaneo lineal (edge cases)
    if not cand:
        cand = {vid for vid, blob in NORMWORDS_BY_ID.items() if phrase_norm in blob}
    # refinamiento: palabra a palabra (evita 'betuel' vs 'betel')
    pat = re.compile(rf"(?:^|\s){re.escape(phrase_norm)}(?:\s|$)")
    return {vid for vid in cand if pat.search(NORMWORDS_BY_ID.get(vid, ""))}

def ids_for_token(token: str) -> Set[str]:
    """Consulta literal por una sola palabra; incluye versión singular/plural simple."""
    t = norm_words(token)
    cand = set(POSTINGS.get(t, set()))
    # heurística morfológica simple
    if t.endswith("es"): cand |= POSTINGS.get(t[:-2], set())
    if t.endswith("s"):  cand |= POSTINGS.get(t[:-1], set())
    return cand

def literal_search(query: str):
    phrases, tokens = extract_phrases_and_tokens(query)
    literal_ids: Set[str] = set()

    if phrases:
        # todas las frases deben cumplirse (AND)
        groups = [ids_for_phrase(p) for p in phrases]
        literal_ids = set.intersection(*groups) if all(groups) else set()
    else:
        # sin comillas: si hay tokens "buenos", usa OR entre ellos (rápido)
        token_ids = [ids_for_token(t) for t in tokens if len(norm_basic(t)) >= 4]
        for s in token_ids:
            literal_ids |= s

    # materializa resultados
    results = []
    for vid in literal_ids:
        ref = REF_BY_ID.get(vid, "")
        txt = index_meta_text(vid)
        results.append({"id": vid, "ref": ref, "texto": txt, "score": 1.0})

    # orden
    results.sort(key=lambda r: canon_sort_key(r["ref"]))  # canónico
    return results

def index_meta_text(vid: str) -> str:
    # preferimos metadata en Pinecone (campo 'contenido') si viene por query semántica;
    # aquí, como estamos en modo literal local, usamos JSONL (rápido y completo).
    return TEXT_BY_ID.get(vid, "")

# =============== pipeline principal ===============
def consultar(pregunta: str, top_k: int = 50):
    clear_screen()

    # 1) intento literal (preciso, sin sinónimos)
    literal = literal_search(pregunta)
    if literal:
        print(f"🔎 Pregunta (literal): {pregunta}\n")
        for r in (literal[:top_k] if top_k else literal):
            print(f"[{r['ref']}]")
            print(r["texto"], "\n")
        # si quieres además 'candidatos semánticos cercanos', se puede añadir debajo
        return

    # 2) sin resultados literales → respaldo semántico (explicitarlo al usuario)
    phrases, tokens = extract_phrases_and_tokens(pregunta)
    sample_k = max(top_k, 200) if (phrases or tokens) else max(top_k, 100)
    sem = pinecone_semantic_candidates(pregunta, top_k, sample_k)

    if not sem:
        # 3) nada semántico: informar y sugerir alternativas automáticas por cercanía léxica
        print(f"🔎 Pregunta: {pregunta}\n")
        print("No encontré coincidencias literales ni semánticas.")
        # sugerencias básicas por similitud de cadenas (no diccionario)
        vocab = sorted(POSTINGS.keys())
        sugg = []
        for t in tokens:
            tnorm = norm_words(t)
            sugg.extend(difflib.get_close_matches(tnorm, vocab, n=5, cutoff=0.8))
        if sugg:
            print("\nQuizá quisiste decir alguna de estas formas (ortografía/diacríticos):")
            print(", ".join(sorted(set(sugg))[:10]))
        print("\nConsejos: usa comillas para frases exactas, verifica ortografía/diacríticos.\n")
        return

    # 4) tenemos semánticos: ordenar y mostrar
    if ORDER_MODE == "canon":
        sem.sort(key=lambda r: canon_sort_key(r["ref"]))
    else:
        sem.sort(key=lambda r: r["score"], reverse=True)

    print(f"🔎 Pregunta (semántica – no hubo coincidencias literales): {pregunta}\n")
    for r in sem[:top_k]:
        print(f"[{r['ref']}] (score={r['score']:.3f})")
        print(r["texto"], "\n")

# =============== CLI ===============
if __name__ == "__main__":
    while True:
        try:
            q = input("\nEscribe tu pregunta (o ENTER para salir): ").strip()
        except EOFError:
            break
        if not q:
            break
        consultar(q, top_k=50)

copy "d:\myapps\scripturedb\pinecone\versiculos.jsonl" "d:\myapps\scripturedb\apicone\"
