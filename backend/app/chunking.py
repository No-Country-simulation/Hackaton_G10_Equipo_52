"""Chunking: divide los documentos en fragmentos con ids estables (chunk_000, chunk_001, ...)."""
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from .config import config
from .ingesta import ErrorIngesta

_ENCABEZADOS = [("#", "h1"), ("##", "h2"), ("###", "h3")]


def dividir(documentos: list[Document]) -> list[Document]:
    recursivo = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap, separators=["\n\n", "\n", ". ", " ", ""]
    )
    fragmentos: list[Document] = []
    for doc in documentos:
        if doc.metadata.get("tipo") == "md":
            # Markdown: primero por títulos, así cada fragmento conserva su sección
            secciones = MarkdownHeaderTextSplitter(_ENCABEZADOS, strip_headers=False).split_text(doc.page_content)
            for s in secciones:
                ruta = " > ".join(s.metadata[k] for k in ("h1", "h2", "h3") if k in s.metadata)
                s.metadata = {**doc.metadata, "seccion": ruta}
            fragmentos += recursivo.split_documents(secciones)
        else:
            fragmentos += recursivo.split_documents([doc])

    if len(fragmentos) > config.max_chunks:
        raise ErrorIngesta("El documento es demasiado extenso. Prueba con uno más corto o divídelo en partes.")
    for i, f in enumerate(fragmentos):
        f.metadata.setdefault("seccion", "")
        f.metadata["chunk_id"] = f"chunk_{i:03d}"
    return fragmentos