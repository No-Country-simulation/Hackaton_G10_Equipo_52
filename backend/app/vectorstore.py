"""Vector store: ChromaDB persistente, una colección por documento (doc_id = hash del contenido)."""
import hashlib
import threading

import chromadb
from langchain_core.documents import Document

from .config import config
from .embeddings import obtener_embeddings

_cliente = None
_candado = threading.Lock()


def _chroma():
    global _cliente
    if _cliente is None:
        _cliente = chromadb.PersistentClient(path=config.chroma_path)
    return _cliente


def calcular_doc_id(fragmentos: list[Document]) -> str:
    huella = hashlib.sha256("\x1f".join(f.page_content for f in fragmentos).encode()).hexdigest()
    return huella[:16]


def indexar(fragmentos: list[Document]) -> str:
    """Indexa los fragmentos y devuelve el doc_id. Si el documento ya estaba indexado, no gasta cuota."""
    doc_id = calcular_doc_id(fragmentos)
    with _candado:
        coleccion = _chroma().get_or_create_collection(f"doc_{doc_id}")
        if coleccion.count() != len(fragmentos):
            _chroma().delete_collection(f"doc_{doc_id}")
            coleccion = _chroma().get_or_create_collection(f"doc_{doc_id}")
            textos = [f.page_content for f in fragmentos]
            coleccion.add(
                ids=[f.metadata["chunk_id"] for f in fragmentos],
                documents=textos,
                metadatas=[{k: v for k, v in f.metadata.items() if v is not None} for f in fragmentos],
                embeddings=obtener_embeddings().embed_documents(textos),
            )
    return doc_id


def _a_dicts(ids, documentos, metadatos) -> list[dict]:
    return [{"id": i, "texto": t, "metadata": m or {}} for i, t, m in zip(ids, documentos, metadatos)]


def recuperar(doc_id: str, consulta: str, k: int = 6) -> list[dict]:
    coleccion = _chroma().get_collection(f"doc_{doc_id}")
    r = coleccion.query(
        query_embeddings=[obtener_embeddings().embed_query(consulta)],
        n_results=min(k, coleccion.count()),
        include=["documents", "metadatas"],
    )
    return _a_dicts(r["ids"][0], r["documents"][0], r["metadatas"][0])


def contexto(doc_id: str, consultas: list[str], k: int = 4, maximo: int = 12) -> list[dict]:
    """Fragmentos más relevantes para varias consultas, sin repetir y en el orden del documento.
    Si el documento es corto, devuelve todo (cobertura completa)."""
    coleccion = _chroma().get_collection(f"doc_{doc_id}")
    if coleccion.count() <= maximo:
        r = coleccion.get(include=["documents", "metadatas"])
        elegidos = {x["id"]: x for x in _a_dicts(r["ids"], r["documents"], r["metadatas"])}
    else:
        elegidos = {}
        for consulta in consultas:
            for x in recuperar(doc_id, consulta, k):
                elegidos.setdefault(x["id"], x)
    return sorted(elegidos.values(), key=lambda x: x["id"])[:maximo]