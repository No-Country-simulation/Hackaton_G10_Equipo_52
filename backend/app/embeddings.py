"""Embeddings: Gemini por defecto; 'fake' (determinista, sin red) solo para pruebas."""
import hashlib
import math
import re

from langchain_core.embeddings import Embeddings

from .config import ErrorConfiguracion, config


class EmbeddingsFalsos(Embeddings):
    """Bolsa de palabras con hashing: textos con palabras en común quedan cerca. Solo para pruebas."""

    DIM = 256

    def _vector(self, texto: str) -> list[float]:
        v = [0.0] * self.DIM
        for palabra in re.findall(r"\w+", texto.lower()):
            v[int(hashlib.md5(palabra.encode()).hexdigest(), 16) % self.DIM] += 1.0
        norma = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norma for x in v]

    def embed_documents(self, textos: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in textos]

    def embed_query(self, texto: str) -> list[float]:
        return self._vector(texto)


def obtener_embeddings() -> Embeddings:
    """Un solo punto para cambiar de proveedor. Ojo: si se cambia el modelo hay que reindexar."""
    if config.embedding_provider == "fake":
        return EmbeddingsFalsos()
    if not config.google_api_key:
        raise ErrorConfiguracion("Falta GOOGLE_API_KEY_EMBEDDINGS")
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(model=config.embedding_model, google_api_key=config.google_api_key_embeddings)