"""API FastAPI. Contrato con el frontend: POST /adaptar → job_id; GET /adaptar/{job_id} → estado y resultado."""
import logging
import re
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from . import jobs, pipeline, storage
from .config import config
from .ingesta import EXTENSIONES, ErrorIngesta, extension, nombre_seguro
from .schemas import EstadoTarea, Parametros, RespuestaAdaptacion, SolicitudAdaptacion

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("krystal")


@asynccontextmanager
async def ciclo_de_vida(_app):
    if not config.oci_enabled:
        log.warning("OCI_ENABLED=false: los archivos se guardan en disco. Para la entrega hay que activar OCI Object Storage.")
    yield


app = FastAPI(title="Krystal API", version="1.0", lifespan=ciclo_de_vida)
app.add_middleware(CORSMiddleware, allow_origins=config.cors_origins, allow_methods=["*"], allow_headers=["*"])


def _mensaje_validacion(errores: list[dict]) -> str:
    campos = sorted({str(e["loc"][-1]) for e in errores if e.get("loc")})
    return "Datos inválidos o incompletos en: " + ", ".join(campos) + "." if campos else "Datos inválidos."


@app.exception_handler(RequestValidationError)
async def _validacion(_request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": _mensaje_validacion(exc.errors())})


def _sesion_segura(session_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "", session_id)[:64] or "anonima"


def _parametros(**campos) -> Parametros:
    try:
        return Parametros(**campos)
    except ValidationError as e:
        raise HTTPException(422, _mensaje_validacion(e.errors()))


@app.get("/salud")
def salud():
    return {"estado": "ok", "almacenamiento": storage.modo(), "modelo": config.llm_model}


@app.post("/adaptar", status_code=202)
async def crear_tarea(
    fondo: BackgroundTasks,
    archivos: list[UploadFile] = File(...),
    perfil_destinatario: str = Form(...),
    formato_salida: str = Form(...),
    nicho_sector: str = Form("General"),
    nivel_detalle: str = Form("Didactico"),
    session_id: str = Form("anonima"),
):
    params = _parametros(
        perfil_destinatario=perfil_destinatario, formato_salida=formato_salida,
        nicho_sector=nicho_sector, nivel_detalle=nivel_detalle,
    )
    if not 1 <= len(archivos) <= config.max_archivos:
        raise HTTPException(422, f"Sube entre 1 y {config.max_archivos} archivos.")

    cargados = []
    for archivo in archivos:
        nombre = nombre_seguro(archivo.filename)
        if extension(nombre) not in EXTENSIONES:
            raise HTTPException(415, f"'{nombre}': formato no soportado. Usa PDF, Markdown o texto.")
        datos = await archivo.read(config.max_mb * 1024 * 1024 + 1)
        if len(datos) > config.max_mb * 1024 * 1024:
            raise HTTPException(413, f"'{nombre}' supera los {config.max_mb} MB.")
        if not datos:
            raise HTTPException(422, f"'{nombre}' está vacío.")
        cargados.append((nombre, datos))

    id_tarea = jobs.crear()
    fondo.add_task(pipeline.ejecutar_tarea, id_tarea, cargados, params, _sesion_segura(session_id))
    return {"job_id": id_tarea}


@app.get("/adaptar/{job_id}", response_model=EstadoTarea, response_model_exclude_none=True)
def consultar_tarea(job_id: str):
    tarea = jobs.obtener(job_id)
    if not tarea:
        raise HTTPException(404, "La tarea no existe o ya expiró. Vuelve a subir tu documento.")
    return tarea


@app.post("/adaptar/sincrono", response_model=RespuestaAdaptacion)
def adaptar_sincrono(solicitud: SolicitudAdaptacion):
    """Variante del ejemplo de la consigna: recibe el texto en JSON y devuelve el paquete completo."""
    try:
        return pipeline.procesar(
            None, solicitud, "anonima", texto=solicitud.documento_contenido,
            titulo=solicitud.documento_titulo, incluir_diagnostico=False,
        )
    except ErrorIngesta as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(502, pipeline.traducir_error(e))