"""Verificación de fidelidad: capa determinista (las citas deben existir) combinada con el juez LLM."""


def verificar_citas(items: list, ids_validos: set[str]) -> tuple[float, list[str]]:
    """Quita las citas a fragmentos inexistentes. Devuelve (proporción de items con alguna cita válida, ids inválidos)."""
    con_respaldo = 0
    invalidas: set[str] = set()
    for item in items:
        validas = [f for f in item.fuentes if f in ids_validos]
        invalidas.update(f for f in item.fuentes if f not in ids_validos)
        item.fuentes = validas
        con_respaldo += bool(validas)
    return (con_respaldo / len(items) if items else 0.0), sorted(invalidas)


def combinar(puntaje_llm: float, proporcion_citas: float) -> float:
    """Puntaje final de anclaje: el del juez, penalizado por los items sin cita válida."""
    return round(max(0.0, min(1.0, puntaje_llm)) * proporcion_citas, 2)