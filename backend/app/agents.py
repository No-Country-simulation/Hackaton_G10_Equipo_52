"""Grafo de LangGraph: router → (evaluador) | (investigador → redactor → revisor ↺)."""
import logging
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from . import prompts, vectorstore
from .config import ErrorConfiguracion, config
from .fidelidad import combinar, verificar_citas
from .schemas import GENERACION_POR_FORMATO, PreguntaDiagnostico

log = logging.getLogger("krystal.agents")

# Etapa (1 a 3) que ve el usuario cuando termina cada nodo
ETAPA_AL_TERMINAR = {"investigador": 2, "redactor": 3}


class ErrorGeneracion(RuntimeError):
    """El modelo no devolvió una respuesta válida. El mensaje es apto para el usuario."""


class Revision(BaseModel):
    anclaje_score: float = Field(ge=0, le=1)
    claridad_pedagogica: Literal["Alta", "Media", "Baja"]
    observaciones: str = ""


class PreguntasGeneradas(BaseModel):
    preguntas: list[PreguntaDiagnostico] = Field(min_length=3)


class Estado(TypedDict, total=False):
    tarea: str  # "adaptar" | "diagnostico"
    params: dict
    titulo: str
    doc_id: str
    contexto: list[dict]
    generacion: BaseModel
    revision: Revision
    anclaje: float
    intentos: int
    observaciones: str
    preguntas: list[PreguntaDiagnostico]


def crear_llm():
    if not config.google_api_key:
        raise ErrorConfiguracion("Falta GOOGLE_API_KEY")
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=config.llm_model, temperature=0.3, google_api_key=config.google_api_key)


def invocar(llm, esquema, prompt: str, intentos: int = 2):
    """Pide una salida estructurada y valida con Pydantic; reintenta si el JSON es inválido."""
    ultimo = None
    for _ in range(intentos):
        try:
            resultado = llm.with_structured_output(esquema).invoke(prompt)
            if resultado is not None:
                return resultado
        except ValueError as e:  # incluye ValidationError y errores de parseo
            ultimo = e
            log.warning("Salida inválida del modelo (%s): %s", esquema.__name__, e)
    raise ErrorGeneracion("La IA devolvió una respuesta inválida. Intenta de nuevo.") from ultimo


def construir_grafo(llm):
    def router(s: Estado) -> str:
        return "evaluador" if s["tarea"] == "diagnostico" else "investigador"

    def investigador(s: Estado):  # sin LLM: solo recupera fragmentos
        p = s["params"]
        consultas = [s["titulo"], "conceptos clave y definiciones", "pasos, procesos y ejemplos", f"aplicación en {p['nicho_sector']}"]
        return {"contexto": vectorstore.contexto(s["doc_id"], consultas), "intentos": 0, "observaciones": ""}

    def redactor(s: Estado):
        p = s["params"]
        prompt = prompts.prompt_redactor(p, s["titulo"], s["contexto"], s.get("observaciones", ""))
        return {"generacion": invocar(llm, GENERACION_POR_FORMATO[p["formato_salida"]], prompt)}

    def revisor(s: Estado):
        gen = s["generacion"]
        proporcion, invalidas = verificar_citas(gen.items, {c["id"] for c in s["contexto"]})
        rev = invocar(llm, Revision, prompts.prompt_revisor(s["contexto"], gen.model_dump_json()))
        notas = [rev.observaciones.strip()] if rev.observaciones.strip() else []
        if invalidas:
            notas.append("Se descartaron citas a fragmentos inexistentes: " + ", ".join(invalidas) + ".")
        if proporcion < 1:
            notas.append(f"{round((1 - proporcion) * len(gen.items))} elemento(s) sin cita válida a la fuente.")
        return {
            "revision": rev,
            "anclaje": combinar(rev.anclaje_score, proporcion),
            "intentos": s["intentos"] + 1,
            "observaciones": " ".join(notas),
        }

    def decidir(s: Estado) -> str:
        reintentar = s["anclaje"] < config.umbral_fidelidad and s["intentos"] <= config.max_reintentos
        return "redactor" if reintentar else END

    def evaluador(s: Estado):
        fragmentos = vectorstore.contexto(s["doc_id"], ["conceptos fundamentales y definiciones", "procesos y componentes principales"], k=5, maximo=8)
        r = invocar(llm, PreguntasGeneradas, prompts.prompt_diagnostico(fragmentos, 5))
        return {"preguntas": r.preguntas[:5]}

    g = StateGraph(Estado)
    for nombre, nodo in (("investigador", investigador), ("redactor", redactor), ("revisor", revisor), ("evaluador", evaluador)):
        g.add_node(nombre, nodo)
    g.add_conditional_edges(START, router, {"evaluador": "evaluador", "investigador": "investigador"})
    g.add_edge("investigador", "redactor")
    g.add_edge("redactor", "revisor")
    g.add_conditional_edges("revisor", decidir, {"redactor": "redactor", END: END})
    g.add_edge("evaluador", END)
    return g.compile()


def ejecutar_adaptacion(llm, params: dict, titulo: str, doc_id: str, al_avanzar=None) -> Estado:
    estado: Estado = {}
    inicial = {"tarea": "adaptar", "params": params, "titulo": titulo, "doc_id": doc_id}
    for evento in construir_grafo(llm).stream(inicial, stream_mode="updates"):
        for nodo, cambios in evento.items():
            estado.update(cambios)
            if al_avanzar and nodo in ETAPA_AL_TERMINAR:
                al_avanzar(ETAPA_AL_TERMINAR[nodo])
    return estado


def ejecutar_diagnostico(llm, doc_id: str) -> list[PreguntaDiagnostico]:
    final = construir_grafo(llm).invoke({"tarea": "diagnostico", "doc_id": doc_id, "titulo": "", "params": {}})
    return final["preguntas"]