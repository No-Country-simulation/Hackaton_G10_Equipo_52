import os
import tempfile
import uuid

_tmp = tempfile.mkdtemp()  # carpetas temporales: los tests no tocan nada del proyecto
os.environ.update({
    "EMBEDDING_PROVIDER": "fake", "CHROMA_PATH": f"{_tmp}/chroma", "LOCAL_STORE": f"{_tmp}/store",
    "OCI_ENABLED": "false", "GOOGLE_API_KEY": "", "UMBRAL_FIDELIDAD": "0.85", "MAX_REINTENTOS": "2",
})

import pytest  # noqa: E402

from app.schemas import ItemFlashcard, ItemPaso, ItemQuiz, PreguntaDiagnostico  # noqa: E402

TEXTO = (
    "Una VCN (Virtual Cloud Network) es una red privada y personalizable configurada en Oracle Cloud Infrastructure. "
    "Ofrece control total sobre el entorno de red, incluyendo subredes públicas y privadas, tablas de enrutamiento, "
    "Internet Gateways, NAT Gateways y Security Lists para controlar el tráfico con reglas de entrada y salida."
)


def texto_unico() -> str:
    """Cada test usa un documento distinto para no compartir caché ni índice."""
    return f"{TEXTO} Identificador {uuid.uuid4().hex}."


class _Salida:
    def __init__(self, llm, esquema):
        self.llm, self.esquema = llm, esquema

    def invoke(self, prompt):
        self.llm.llamadas.append(self.esquema.__name__)
        return self.llm.responder(self.esquema)


class FakeLLM:
    """LLM de prueba: devuelve salidas estructuradas válidas sin llamar a ninguna API."""

    def __init__(self, anclajes=None, cita="chunk_000", falla=False):
        self.anclajes, self.cita, self.falla, self.llamadas = list(anclajes or [0.95]), cita, falla, []

    def with_structured_output(self, esquema):
        return _Salida(self, esquema)

    def responder(self, esquema):
        if self.falla:
            raise ValueError("JSON inválido")
        nombre, fuentes = esquema.__name__, [self.cita]
        if nombre == "Revision":
            puntaje = self.anclajes.pop(0) if len(self.anclajes) > 1 else self.anclajes[0]
            return esquema(anclaje_score=puntaje, claridad_pedagogica="Alta", observaciones="Revisión de prueba.")
        if nombre == "PreguntasGeneradas":
            return esquema(preguntas=[
                PreguntaDiagnostico(pregunta=f"Pregunta de prueba {i}", opciones=["a", "b", "c", "d"], correcta=i % 4)
                for i in range(5)
            ])
        base = dict(
            titulo="Título de prueba", introduccion_contextualizada="Introducción de prueba para el material.",
            conceptos_clave=["VCN"], prerrequisitos=["Redes"],
        )
        if nombre == "GeneracionFlashcards":
            items = [ItemFlashcard(frente=f"Frente {i}", dorso=f"Dorso {i}", fuentes=list(fuentes)) for i in range(4)]
        elif nombre == "GeneracionQuiz":
            items = [ItemQuiz(pregunta=f"Pregunta {i}?", opciones=["a", "b", "c", "d"], respuesta_correcta=1,
                              justificacion="Porque sí.", fuentes=list(fuentes)) for i in range(4)]
        else:
            items = [ItemPaso(titulo_paso=f"Paso {i}", texto=f"Texto {i}", fuentes=list(fuentes)) for i in range(4)]
        return esquema(items=items, **base)


@pytest.fixture
def llm(monkeypatch):
    falso = FakeLLM()
    monkeypatch.setattr("app.agents.crear_llm", lambda: falso)
    return falso