"""Grafo de LangGraph: router → (evaluador) | (investigador → redactor → revisor ↺)."""
import logging
import time
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
PAUSAS_LIMITE = (8, 20, 40)  # segundos de espera si TODOS los modelos limitan la velocidad (error 429)
TIEMPO_MAXIMO_S = 60  # un pedido que no responde en este tiempo se corta (y se pasa al respaldo, si hay)


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


# ---------- Clasificación de errores del proveedor ----------
def _estado_http(e: Exception) -> int | None:
    for atributo in ("status_code", "code"):
        valor = getattr(e, atributo, None)
        if isinstance(valor, int):
            return valor
    return None


def _es_limite_de_velocidad(e: Exception) -> bool:
    texto = str(e).lower()
    return _estado_http(e) == 429 or any(x in texto for x in ("rate limit", "rate_limit", "resource_exhausted", "quota"))


def _es_salida_invalida(e: Exception) -> bool:
    """Groq responde 400 'tool_use_failed' cuando el modelo arma mal la salida estructurada."""
    texto = str(e).lower()
    return any(x in texto for x in ("tool_use_failed", "failed to call a function", "failed_generation", "json_validate_failed"))


def _conviene_respaldo(e: Exception) -> bool:
    """¿Vale la pena probar con el modelo de respaldo? Sí si el proveedor limita, falla, no existe o no responde."""
    estado = _estado_http(e)
    if estado is not None and (estado in (401, 403, 404, 408, 429) or estado >= 500):
        return True
    texto = str(e).lower()
    return _es_limite_de_velocidad(e) or any(
        x in texto for x in ("overloaded", "unavailable", "not_found", "no longer available", "decommissioned",
                             "timed out", "timeout", "connection error", "api key not valid", "invalid_api_key")
    )


# ---------- Modelos de lenguaje ----------
def _crear_modelo(proveedor: str, modelo: str, clave: str = ""):
    if proveedor == "groq":
        clave = clave or config.llm_respaldo_api_key
        if not clave:
            raise ErrorConfiguracion("Falta GROQ_API_KEY")
        from langchain_groq import ChatGroq

        return ChatGroq(model=modelo, temperature=0.3, api_key=clave, max_retries=1, timeout=TIEMPO_MAXIMO_S)
    if proveedor == "gemini":
        clave = clave or config.google_api_key
        if not clave:
            raise ErrorConfiguracion("Falta GOOGLE_API_KEY")
        from langchain_google_genai import ChatGoogleGenerativeAI

        # max_retries=1: si Gemini limita, el error aparece enseguida (y puede actuar el respaldo)
        # en vez de quedarse esperando con reintentos internos
        return ChatGoogleGenerativeAI(model=modelo, temperature=0.3, google_api_key=clave, max_retries=1, timeout=TIEMPO_MAXIMO_S)
    raise ErrorConfiguracion(f"LLM_PROVIDER desconocido: '{proveedor}' (usa groq o gemini)")


class _SalidaConRespaldo:
    def __init__(self, principal, respaldo):
        self.principal, self.respaldo = principal, respaldo

    def invoke(self, prompt: str):
        try:
            return self.principal.invoke(prompt)
        except ValueError:
            raise  # JSON inválido: lo maneja invocar(), reintentando con el mismo modelo
        except Exception as e:
            if self.respaldo is None or not _conviene_respaldo(e):
                raise
            log.warning("Falló el modelo principal (%s: %s); se usa el de respaldo", type(e).__name__, str(e)[:120])
            return self.respaldo.invoke(prompt)


class LLMConRespaldo:
    """Un modelo principal con un respaldo opcional (otro proveedor, otro modelo u otra clave)."""

    def __init__(self, principal, respaldo=None):
        self.principal, self.respaldo = principal, respaldo
        self.rapido = self  # se reemplaza por un modelo más liviano si hay LLM_MODEL_RAPIDO

    def with_structured_output(self, esquema):
        respaldo = self.respaldo.with_structured_output(esquema) if self.respaldo is not None else None
        return _SalidaConRespaldo(self.principal.with_structured_output(esquema), respaldo)


def crear_llm():
    """Modelo principal (redacción) + modelo rápido (revisión y diagnóstico) + respaldo opcional."""
    respaldo = None
    if config.llm_respaldo_provider:
        try:
            respaldo = _crear_modelo(config.llm_respaldo_provider, config.llm_respaldo_model, config.llm_respaldo_api_key)
        except ErrorConfiguracion as e:
            log.warning("El modelo de respaldo no está disponible: %s", e)
    llm = LLMConRespaldo(_crear_modelo(config.llm_provider, config.llm_model), respaldo)
    if config.llm_model_rapido and config.llm_model_rapido != config.llm_model:
        llm.rapido = LLMConRespaldo(_crear_modelo(config.llm_provider, config.llm_model_rapido), respaldo)
    return llm


def invocar(llm, esquema, prompt: str, intentos: int = 3):
    """Pide una salida estructurada validada con Pydantic.
    Reintenta si el JSON es inválido y espera si el proveedor limita la velocidad (429)."""
    ultimo = None
    pausas = iter(PAUSAS_LIMITE)
    for _ in range(intentos):
        resultado = None
        while True:
            try:
                resultado = llm.with_structured_output(esquema).invoke(prompt)
                break
            except ValueError as e:  # incluye ValidationError y errores de parseo
                ultimo = e
                log.warning("Salida inválida del modelo (%s): %s", esquema.__name__, e)
                break
            except Exception as e:
                if _es_limite_de_velocidad(e):
                    pausa = next(pausas, None)
                    if pausa is None:
                        raise ErrorGeneracion("El modelo de IA está saturado en este momento. Espera un minuto e intenta de nuevo.") from e
                    log.warning("El modelo limitó la velocidad; reintentando en %s s", pausa)
                    time.sleep(pausa)
                    continue
                if _es_salida_invalida(e):
                    ultimo = e
                    log.warning("El modelo armó mal la salida estructurada (%s)", esquema.__name__)
                    break
                raise
        if resultado is not None:
            return resultado
    raise ErrorGeneracion("La IA devolvió una respuesta inválida. Intenta de nuevo.") from ultimo


# ---------- Grafo ----------
def construir_grafo(llm):
    rapido = getattr(llm, "rapido", llm)  # modelo liviano para revisar y para el diagnóstico

    def router(s: Estado) -> str:
        return "evaluador" if s["tarea"] == "diagnostico" else "investigador"

    def investigador(s: Estado):  # sin LLM: solo recupera fragmentos
        p = s["params"]
        consultas = [
            f"{s['titulo']}. Conceptos clave y definiciones",
            f"Pasos, procesos y ejemplos de aplicación en {p['nicho_sector']}",
        ]
        return {"contexto": vectorstore.contexto(s["doc_id"], consultas, maximo=config.max_contexto), "intentos": 0, "observaciones": ""}

    def redactor(s: Estado):
        p = s["params"]
        prompt = prompts.prompt_redactor(p, s["titulo"], s["contexto"], s.get("observaciones", ""))
        return {"generacion": invocar(llm, GENERACION_POR_FORMATO[p["formato_salida"]], prompt)}

    def revisor(s: Estado):
        gen = s["generacion"]
        proporcion, invalidas = verificar_citas(gen.items, {c["id"] for c in s["contexto"]})
        # El juez solo necesita los fragmentos que el contenido cita: menos tokens y menos tiempo
        citados = {f for it in gen.items for f in it.fuentes}
        a_revisar = [c for c in s["contexto"] if c["id"] in citados] or s["contexto"]
        rev = invocar(rapido, Revision, prompts.prompt_revisor(a_revisar, gen.model_dump_json()))
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
        fragmentos = vectorstore.contexto(
            s["doc_id"],
            ["conceptos fundamentales y definiciones", "procesos y componentes principales"],
            k=5,
            maximo=config.max_contexto,
        )
        r = invocar(rapido, PreguntasGeneradas, prompts.prompt_diagnostico(fragmentos, 5))
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