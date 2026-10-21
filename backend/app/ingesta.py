"""Ingesta: lee PDF, Markdown y texto plano y devuelve Documents de LangChain con metadata."""
import io
import os
import re

from langchain_core.documents import Document
from pypdf import PdfReader

from .config import config

EXTENSIONES = (".pdf", ".md", ".markdown", ".txt")
MIN_CARACTERES = 50


class ErrorIngesta(ValueError):
    """El documento no se puede procesar. El mensaje es apto para mostrarse al usuario."""


def extension(nombre: str) -> str:
    return os.path.splitext(nombre or "")[1].lower()


def nombre_seguro(nombre: str | None) -> str:
    """Solo el nombre del archivo, sin rutas ni caracteres raros (se usa en nombres de objeto OCI)."""
    base = os.path.basename((nombre or "documento").replace("\\", "/"))
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(" .")
    return (base or "documento")[:120]


def limpiar(texto: str) -> str:
    texto = texto.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    texto = re.sub(r"-\n(?=[a-záéíóúñ])", "", texto)  # palabras cortadas por guion al final de línea
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def _decodificar(datos: bytes) -> str:
    try:
        return datos.decode("utf-8-sig")
    except UnicodeDecodeError:
        return datos.decode("latin-1")


def cargar_documento(nombre: str, datos: bytes) -> list[Document]:
    nombre = nombre_seguro(nombre)
    ext = extension(nombre)
    if ext not in EXTENSIONES:
        raise ErrorIngesta(f"'{nombre}': formato no soportado. Usa PDF, Markdown o texto.")
    if not datos:
        raise ErrorIngesta(f"'{nombre}' está vacío.")

    documentos: list[Document] = []
    if ext == ".pdf":
        try:
            lector = PdfReader(io.BytesIO(datos))
            if lector.is_encrypted:
                raise ErrorIngesta(f"'{nombre}' está protegido con contraseña.")
            if len(lector.pages) > config.max_paginas:
                raise ErrorIngesta(f"'{nombre}' tiene más de {config.max_paginas} páginas.")
            for i, pagina in enumerate(lector.pages, start=1):
                texto = limpiar(pagina.extract_text() or "")
                if texto:
                    documentos.append(Document(page_content=texto, metadata={"fuente": nombre, "pagina": i, "tipo": "pdf"}))
        except ErrorIngesta:
            raise
        except Exception as e:
            raise ErrorIngesta(f"No pudimos leer '{nombre}' (¿está dañado?).") from e
    else:
        texto = limpiar(_decodificar(datos))
        if texto:
            tipo = "md" if ext in (".md", ".markdown") else "txt"
            documentos.append(Document(page_content=texto, metadata={"fuente": nombre, "tipo": tipo}))

    if sum(len(d.page_content) for d in documentos) < MIN_CARACTERES:
        raise ErrorIngesta(f"No pudimos extraer texto de '{nombre}'. Si es un PDF escaneado, aún no lo soportamos.")
    return documentos


def cargar_texto(titulo: str, contenido: str) -> list[Document]:
    """Texto pegado directamente en la solicitud (JSON de la consigna)."""
    texto = limpiar(contenido)
    if len(texto) < MIN_CARACTERES:
        raise ErrorIngesta("El contenido del documento es demasiado corto.")
    return [Document(page_content=texto, metadata={"fuente": nombre_seguro(titulo), "tipo": "txt"})]