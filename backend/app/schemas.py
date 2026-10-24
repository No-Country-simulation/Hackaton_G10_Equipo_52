"""Esquemas de entrada y salida con tipado estricto (Pydantic)."""
import unicodedata
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PERFILES = ("Principiante", "Intermedio", "Avanzado", "Ejecutivo")
FORMATOS = ("Resumen", "Flashcards", "Quiz", "Tutorial")
NICHOS = (
    "General", "Educacion", "Salud", "Finanzas", "Fintech", "Comercio", "E-commerce", "Gastronomia", "Agro",
    "Industria", "Logistica", "Gobierno", "Arte", "Tecnologia", "Social", "Legal", "Construccion",
)
DETALLES = ("Conciso", "Didactico", "Profundo")

Perfil = Literal["Principiante", "Intermedio", "Avanzado", "Ejecutivo"]
Formato = Literal["Resumen", "Flashcards", "Quiz", "Tutorial"]
Nicho = Literal[
    "General", "Educacion", "Salud", "Finanzas", "Fintech", "Comercio", "E-commerce", "Gastronomia", "Agro",
    "Industria", "Logistica", "Gobierno", "Arte", "Tecnologia", "Social", "Legal", "Construccion",
]
Detalle = Literal["Conciso", "Didactico", "Profundo"]


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _canonico(valor, opciones):
    """Acepta mayúsculas/minúsculas y tildes ('Educación' → 'Educacion')."""
    if isinstance(valor, str):
        buscado = _sin_tildes(valor).strip().lower()
        for opcion in opciones:
            if opcion.lower() == buscado:
                return opcion
    return valor


# ---------- Entrada ----------
class Parametros(BaseModel):
    perfil_destinatario: Perfil
    formato_salida: Formato
    nicho_sector: Nicho = "General"
    nivel_detalle: Detalle = "Didactico"

    @field_validator("perfil_destinatario", mode="before")
    @classmethod
    def _perfil(cls, v):
        return _canonico(v, PERFILES)

    @field_validator("formato_salida", mode="before")
    @classmethod
    def _formato(cls, v):
        return _canonico(v, FORMATOS)

    @field_validator("nicho_sector", mode="before")
    @classmethod
    def _nicho(cls, v):
        return _canonico(v, NICHOS)

    @field_validator("nivel_detalle", mode="before")
    @classmethod
    def _detalle(cls, v):
        return _canonico(v, DETALLES)


class SolicitudAdaptacion(Parametros):
    """Solicitud JSON del ejemplo de la consigna (texto pegado en lugar de archivos)."""

    documento_titulo: str = Field(min_length=3, max_length=200)
    documento_contenido: str = Field(min_length=50, max_length=600_000)


# ---------- Items generados por el LLM, según el formato ----------
class ItemFlashcard(BaseModel):
    frente: str = Field(min_length=3)
    dorso: str = Field(min_length=3)
    pista_didactica: str = ""
    fuentes: list[str] = []


class ItemQuiz(BaseModel):
    pregunta: str = Field(min_length=5)
    opciones: list[str] = Field(min_length=2, max_length=6)
    respuesta_correcta: int = Field(ge=0)
    justificacion: str = Field(min_length=3)
    fuentes: list[str] = []

    @model_validator(mode="after")
    def _correcta_en_rango(self):
        if self.respuesta_correcta >= len(self.opciones):
            raise ValueError("respuesta_correcta debe ser el índice de una opción existente")
        return self


class ItemPaso(BaseModel):
    titulo_paso: str = Field(min_length=3)
    texto: str = Field(min_length=3)
    fuentes: list[str] = []


class _Generacion(BaseModel):
    titulo: str = Field(min_length=3)
    introduccion_contextualizada: str = Field(min_length=10)
    conceptos_clave: list[str] = Field(min_length=1, max_length=12)
    prerrequisitos: list[str] = []


class GeneracionFlashcards(_Generacion):
    items: list[ItemFlashcard] = Field(min_length=3)


class GeneracionQuiz(_Generacion):
    items: list[ItemQuiz] = Field(min_length=3)


class GeneracionPasos(_Generacion):
    items: list[ItemPaso] = Field(min_length=3)


GENERACION_POR_FORMATO = {
    "Flashcards": GeneracionFlashcards,
    "Quiz": GeneracionQuiz,
    "Resumen": GeneracionPasos,
    "Tutorial": GeneracionPasos,
}


class PreguntaDiagnostico(BaseModel):
    pregunta: str = Field(min_length=5)
    opciones: list[str] = Field(min_length=2, max_length=6)
    correcta: int = Field(ge=0)

    @model_validator(mode="after")
    def _correcta_en_rango(self):
        if self.correcta >= len(self.opciones):
            raise ValueError("correcta debe ser el índice de una opción existente")
        return self


# ---------- Salida (JSON de la consigna) ----------
class ContenidoAdaptado(BaseModel):
    titulo: str
    introduccion_contextualizada: str
    items: list[ItemFlashcard | ItemQuiz | ItemPaso]


class Metadatos(BaseModel):
    perfil_aplicado: Perfil
    formato_generado: Formato
    nicho_sector: Nicho
    nivel_detalle: Detalle
    tiempo_estimado_estudio_minutos: int
    conceptos_clave: list[str]
    prerrequisitos: list[str]


class EvaluacionCalidad(BaseModel):
    anclaje_fuente_score: float = Field(ge=0, le=1)
    claridad_pedagogica: Literal["Alta", "Media", "Baja"]
    observaciones: str


class AlmacenamientoOCI(BaseModel):
    bucket: str
    objeto_id: str
    status_upload: str  # completado | local | error


class Diagnostico(BaseModel):
    preguntas: list[PreguntaDiagnostico] = []


class FuenteCitada(BaseModel):
    archivo: str
    pagina: int | None = None
    fragmento: str


class RespuestaAdaptacion(BaseModel):
    status: Literal["exito"] = "exito"
    doc_id: str
    metadatos: Metadatos
    contenido_adaptado: ContenidoAdaptado
    evaluacion_calidad: EvaluacionCalidad
    almacenamiento_oci: AlmacenamientoOCI
    diagnostico: Diagnostico = Diagnostico()
    fuentes_detalle: dict[str, FuenteCitada] = {}


class EstadoTarea(BaseModel):
    estado: Literal["procesando", "listo", "error"]
    etapa: int = 1
    mensaje: str | None = None
    resultado: RespuestaAdaptacion | None = None