"""Tareas en curso, en memoria. Suficiente para el MVP (se pierden al reiniciar el servidor)."""
import threading
import time
import uuid

_candado = threading.Lock()
_tareas: dict[str, dict] = {}
VIDA_S = 2 * 3600


def crear() -> str:
    with _candado:
        ahora = time.time()
        for id_ in [i for i, t in _tareas.items() if ahora - t["creada"] > VIDA_S]:
            del _tareas[id_]
        id_ = uuid.uuid4().hex
        _tareas[id_] = {"estado": "procesando", "etapa": 1, "mensaje": None, "resultado": None, "creada": ahora}
        return id_


def actualizar(id_: str, **campos) -> None:
    with _candado:
        if id_ in _tareas:
            _tareas[id_].update(campos)


def avanzar_etapa(id_: str, etapa: int) -> None:
    with _candado:  # la etapa solo avanza, nunca retrocede
        if id_ in _tareas and etapa > _tareas[id_]["etapa"]:
            _tareas[id_]["etapa"] = etapa


def obtener(id_: str) -> dict | None:
    with _candado:
        tarea = _tareas.get(id_)
        return dict(tarea) if tarea else None