"""Almacenamiento: OCI Object Storage (Always Free). Con OCI_ENABLED=false guarda en disco (solo desarrollo)."""
import logging
import os
import threading
from pathlib import Path

from .config import config

log = logging.getLogger("krystal.storage")
_cliente = None
_candado = threading.Lock()


def modo() -> str:
    return "oci" if config.oci_enabled else "local"


def _oci():
    global _cliente
    with _candado:
        if _cliente is None:
            import oci

            ajustes = oci.config.from_file(os.path.expanduser(config.oci_config_file), config.oci_profile)
            cliente = oci.object_storage.ObjectStorageClient(ajustes)
            _cliente = (cliente, config.oci_namespace or cliente.get_namespace().data)
        return _cliente


def _ruta_local(nombre: str) -> Path:
    base = Path(config.local_store).resolve()
    ruta = (base / nombre).resolve()
    if base not in ruta.parents:
        raise ValueError("Nombre de objeto inválido")
    return ruta


def subir(nombre: str, datos: bytes, content_type: str = "application/json") -> str:
    """Devuelve 'completado' (OCI), 'local' (disco) o 'error'. Un fallo de almacenamiento no tumba la tarea."""
    try:
        if config.oci_enabled:
            cliente, namespace = _oci()
            cliente.put_object(namespace, config.oci_bucket, nombre, datos, content_type=content_type)
            return "completado"
        ruta = _ruta_local(nombre)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(datos)
        return "local"
    except Exception:
        log.exception("No se pudo guardar '%s'", nombre)
        return "error"


def leer(nombre: str) -> bytes | None:
    try:
        if config.oci_enabled:
            cliente, namespace = _oci()
            return cliente.get_object(namespace, config.oci_bucket, nombre).data.content
        ruta = _ruta_local(nombre)
        return ruta.read_bytes() if ruta.exists() else None
    except Exception:
        return None  # no existe (o no se pudo leer): se trata como "sin caché"