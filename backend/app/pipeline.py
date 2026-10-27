"""Orquesta todo el flujo: ingesta → chunking → indexado → grafo de agentes → OCI → resultado."""
import hashlib
import json
import logging
import math
import threading
from concurrent.futures import ThreadPoolExecutor

from . import agents, chunking, jobs, prompts, storage, vectorstore
from .config import ErrorConfiguracion, config
from .ingesta import ErrorIngesta, cargar_documento, cargar_texto, nombre_seguro
from .schemas import (
    AlmacenamientoOCI, ContenidoAdaptado, Diagnostico, EvaluacionCalidad, FuenteCitada, Metadatos, Parametros,
    RespuestaAdaptacion,
)

log = logging.getLogger("krystal.pipeline")
_cupo = threading.Semaphore(config.max_tareas)  # protege la cuota gratuita del modelo


def _minutos(items) -> int:
    palabras = sum(len(str(v).split()) for it in items for v in it.model_dump(exclude={"fuentes"}).values() if v)
    return max(2, math.ceil(palabras / 180))


def _fuentes_detalle(contexto: list[dict], ids: set[str]) -> dict[str, FuenteCitada]:
    detalle = {}
    for c in contexto:
        if c["id"] in ids:
            detalle[c["id"]] = FuenteCitada(
                archivo=c["metadata"].get("fuente", ""), pagina=c["metadata"].get("pagina"), fragmento=c["texto"][:300]
            )
    return detalle


def procesar(
    archivos: list[tuple[str, bytes]] | None,
    params: Parametros,
    session_id: str,
    *,
    texto: str | None = None,
    titulo: str | None = None,
    incluir_diagnostico: bool = True,
    al_avanzar=None,
) -> RespuestaAdaptacion:
    avanzar = al_avanzar or (lambda etapa: None)
    with _cupo:
        # 1) Ingesta, chunking e indexado
        if texto is not None:
            titulo = titulo or "documento"
            documentos = cargar_texto(titulo, texto)
        else:
            documentos = [d for nombre, datos in archivos for d in cargar_documento(nombre, datos)]
            titulo = titulo or archivos[0][0]
        fragmentos = chunking.dividir(documentos)
        doc_id = vectorstore.indexar(fragmentos)

        # 2) Persistir los originales
        if texto is not None:
            storage.subir(f"originales/{session_id}/{doc_id}/{nombre_seguro(titulo)}.txt", texto.encode(), "text/plain")
        else:
            for nombre, datos in archivos:
                storage.subir(f"originales/{session_id}/{doc_id}/{nombre_seguro(nombre)}", datos, "application/octet-stream")

        # 3) Caché: mismo documento + mismos parámetros = mismo resultado, sin gastar cuota
        pedido = {**params.model_dump(), "doc_id": doc_id, "diag": incluir_diagnostico, "v": prompts.VERSION}
        clave = hashlib.sha256(json.dumps(pedido, sort_keys=True).encode()).hexdigest()[:24]
        guardado = storage.leer(f"cache/{clave}.json")
        if guardado:
            try:
                resultado = RespuestaAdaptacion.model_validate_json(guardado)
                avanzar(3)
                return resultado
            except ValueError:
                log.warning("Caché corrupto: %s", clave)

        # 4) Agentes: la adaptación y el diagnóstico corren en paralelo
        llm = agents.crear_llm()
        preguntas = []
        with ThreadPoolExecutor(max_workers=1) as pool:
            diagnostico = pool.submit(agents.ejecutar_diagnostico, llm, doc_id) if incluir_diagnostico else None
            estado = agents.ejecutar_adaptacion(llm, params.model_dump(), titulo, doc_id, al_avanzar=avanzar)
            if diagnostico:
                try:
                    preguntas = diagnostico.result()
                except Exception as e:  # el diagnóstico es opcional: si falla, se omite
                    log.warning("No se pudo generar el diagnóstico: %s", e)
        avanzar(3)

        # 5) Armar el JSON de la consigna y guardarlo en OCI
        gen, rev, anclaje = estado["generacion"], estado["revision"], estado["anclaje"]
        observaciones = estado.get("observaciones", "")
        if anclaje < config.umbral_fidelidad:
            observaciones = f"Advertencia: la fidelidad ({anclaje:.2f}) quedó por debajo del umbral ({config.umbral_fidelidad}). {observaciones}"
        objeto = f"resultados/{session_id}/{doc_id}-{params.perfil_destinatario}-{params.formato_salida}.json".lower()
        resultado = RespuestaAdaptacion(
            doc_id=doc_id,
            metadatos=Metadatos(
                perfil_aplicado=params.perfil_destinatario, formato_generado=params.formato_salida,
                nicho_sector=params.nicho_sector, nivel_detalle=params.nivel_detalle,
                tiempo_estimado_estudio_minutos=_minutos(gen.items),
                conceptos_clave=gen.conceptos_clave, prerrequisitos=gen.prerrequisitos,
            ),
            contenido_adaptado=ContenidoAdaptado(
                titulo=gen.titulo, introduccion_contextualizada=gen.introduccion_contextualizada, items=gen.items
            ),
            evaluacion_calidad=EvaluacionCalidad(
                anclaje_fuente_score=anclaje, claridad_pedagogica=rev.claridad_pedagogica,
                observaciones=observaciones.strip() or "Sin observaciones.",
            ),
            almacenamiento_oci=AlmacenamientoOCI(
                bucket=config.oci_bucket, objeto_id=objeto, status_upload="completado" if config.oci_enabled else "local"
            ),
            diagnostico=Diagnostico(preguntas=preguntas),
            fuentes_detalle=_fuentes_detalle(estado["contexto"], {f for it in gen.items for f in it.fuentes}),
        )
        cuerpo = resultado.model_dump_json().encode()
        estado_subida = storage.subir(objeto, cuerpo)
        storage.subir(f"cache/{clave}.json", cuerpo)
        resultado.almacenamiento_oci.status_upload = estado_subida
        return resultado


def traducir_error(e: Exception) -> str:
    """Convierte cualquier excepción en un mensaje para el usuario (el detalle va al log)."""
    if isinstance(e, (ErrorIngesta, agents.ErrorGeneracion)):
        return str(e)
    if isinstance(e, ErrorConfiguracion):
        log.error("Configuración incompleta: %s", e)
        return "El servicio de IA no está configurado. Avisa al equipo."
    if any(x in str(e).lower() for x in ("429", "quota", "resource_exhausted", "rate limit")):
        return "Se alcanzó el límite de uso del modelo de IA. Espera un minuto e intenta de nuevo."
    log.error("Error inesperado al procesar", exc_info=e)
    return "Ocurrió un error inesperado al procesar tu documento. Intenta de nuevo."


def ejecutar_tarea(job_id: str, archivos: list[tuple[str, bytes]], params: Parametros, session_id: str) -> None:
    """Se ejecuta en segundo plano; el frontend consulta el estado con GET /adaptar/{job_id}."""
    try:
        resultado = procesar(archivos, params, session_id, al_avanzar=lambda etapa: jobs.avanzar_etapa(job_id, etapa))
        jobs.actualizar(job_id, estado="listo", etapa=3, resultado=resultado.model_dump(mode="json"))
    except Exception as e:
        jobs.actualizar(job_id, estado="error", mensaje=traducir_error(e))