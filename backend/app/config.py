"""Configuración del backend: se lee de variables de entorno (ver .env.example)."""
import os

from dotenv import load_dotenv

load_dotenv()


class ErrorConfiguracion(RuntimeError):
    """Falta configurar algo (por ejemplo la clave de Gemini)."""


def _texto(nombre: str, defecto: str = "") -> str:
    return os.getenv(nombre, defecto).split("#")[0].strip()


def _numero(nombre: str, defecto, tipo=int):
    try:
        return tipo(_texto(nombre, str(defecto)))
    except ValueError:
        return defecto


class Config:
    def __init__(self):
        # IA
        self.google_api_key = _texto("GOOGLE_API_KEY")
        self.google_api_key_embeddings = _texto("GOOGLE_API_KEY_EMBEDDINGS") or self.google_api_key
        self.llm_model = _texto("LLM_MODEL", "gemini-3.8-flash")
        self.embedding_provider = _texto("EMBEDDING_PROVIDER", "gemini")
        self.embedding_model = _texto("EMBEDDING_MODEL", "models/gemini-embedding-001")        
        # RAG
        self.chunk_size = _numero("CHUNK_SIZE", 1000)
        self.chunk_overlap = _numero("CHUNK_OVERLAP", 150)
        self.chroma_path = _texto("CHROMA_PATH", "./.chroma")
        # Calidad
        self.umbral_fidelidad = _numero("UMBRAL_FIDELIDAD", 0.85, float)
        self.max_reintentos = _numero("MAX_REINTENTOS", 2)
        # Límites
        self.max_archivos = _numero("MAX_ARCHIVOS", 5)
        self.max_mb = _numero("MAX_MB", 20)
        self.max_paginas = _numero("MAX_PAGINAS", 200)
        self.max_chunks = _numero("MAX_CHUNKS", 400)
        self.max_tareas = _numero("MAX_TAREAS", 1)
        # Red
        self.cors_origins = [o.strip() for o in _texto("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
        # Almacenamiento
        self.oci_enabled = _texto("OCI_ENABLED", "false").lower() in {"1", "true", "si", "yes"}
        self.oci_bucket = _texto("OCI_BUCKET", "krystal-contenidos-educativos")
        self.oci_config_file = _texto("OCI_CONFIG_FILE", "~/.oci/config")
        self.oci_profile = _texto("OCI_PROFILE", "DEFAULT")
        self.oci_namespace = _texto("OCI_NAMESPACE")
        self.local_store = _texto("LOCAL_STORE", "./.local_store")


config = Config()