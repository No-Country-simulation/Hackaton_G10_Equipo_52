from fastapi.testclient import TestClient

from app.main import app
from app.schemas import RespuestaAdaptacion
from tests.conftest import texto_unico
from tests.test_ingesta import pdf_con_texto

cliente = TestClient(app)
FORM = {"perfil_destinatario": "Principiante", "formato_salida": "Flashcards", "nicho_sector": "Educacion", "nivel_detalle": "Didactico", "session_id": "sesion-1"}


def subir(archivos, **extra):
    return cliente.post("/adaptar", data={**FORM, **extra}, files=archivos)


def txt(nombre="manual.txt", texto=None):
    return ("archivos", (nombre, (texto or texto_unico()).encode(), "text/plain"))


def resultado_de(respuesta):
    assert respuesta.status_code == 202
    return cliente.get(f"/adaptar/{respuesta.json()['job_id']}").json()


def test_flujo_completo_cumple_el_contrato_del_frontend(llm):
    tarea = resultado_de(subir([txt()]))
    assert tarea["estado"] == "listo" and tarea["etapa"] == 3
    res = RespuestaAdaptacion.model_validate(tarea["resultado"])
    assert {"status", "metadatos", "contenido_adaptado", "evaluacion_calidad", "almacenamiento_oci", "diagnostico"} <= set(tarea["resultado"])
    assert res.metadatos.formato_generado == "Flashcards" and res.metadatos.nicho_sector == "Educacion"
    assert res.contenido_adaptado.items[0].frente and res.contenido_adaptado.items[0].fuentes == ["chunk_000"]
    assert res.almacenamiento_oci.status_upload == "local" and res.almacenamiento_oci.objeto_id.startswith("resultados/sesion-1/")
    assert len(res.diagnostico.preguntas) == 5 and "chunk_000" in res.fuentes_detalle


def test_acepta_pdf_y_varios_archivos(llm):
    pdf = ("archivos", ("manual.pdf", pdf_con_texto("VCN es una red privada en la nube de Oracle con subredes " + texto_unico()[:80].replace("(", "").replace(")", "")), "application/pdf"))
    assert resultado_de(subir([pdf, txt()], formato_salida="Quiz"))["estado"] == "listo"


def test_mismo_pedido_usa_el_cache(llm):
    texto = texto_unico()
    resultado_de(subir([txt(texto=texto)]))
    llamadas = len(llm.llamadas)
    assert resultado_de(subir([txt(texto=texto)]))["estado"] == "listo" and len(llm.llamadas) == llamadas


def test_session_id_malicioso_se_sanea(llm):
    tarea = resultado_de(subir([txt()], session_id="../../etc/x"))
    assert ".." not in tarea["resultado"]["almacenamiento_oci"]["objeto_id"]


def test_extension_no_soportada():
    r = subir([("archivos", ("a.docx", b"datos", "application/octet-stream"))])
    assert r.status_code == 415 and "formato no soportado" in r.json()["detail"]


def test_demasiados_archivos():
    r = subir([txt(f"a{i}.txt") for i in range(6)])
    assert r.status_code == 422 and "entre 1 y 5" in r.json()["detail"]


def test_archivo_vacio():
    assert subir([("archivos", ("a.txt", b"", "text/plain"))]).status_code == 422


def test_perfil_invalido_da_mensaje_claro():
    r = subir([txt()], perfil_destinatario="Experto")
    assert r.status_code == 422 and "perfil_destinatario" in r.json()["detail"]


def test_sin_archivos():
    r = cliente.post("/adaptar", data=FORM)
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


def test_tarea_inexistente():
    r = cliente.get("/adaptar/noexiste")
    assert r.status_code == 404 and "expiró" in r.json()["detail"]


def test_pdf_sin_texto_termina_en_error_amigable(llm):
    from pypdf import PdfWriter
    import io
    escritor, buffer = PdfWriter(), io.BytesIO()
    escritor.add_blank_page(100, 100)
    escritor.write(buffer)
    tarea = resultado_de(subir([("archivos", ("escaneado.pdf", buffer.getvalue(), "application/pdf"))]))
    assert tarea["estado"] == "error" and "PDF escaneado" in tarea["mensaje"]


def test_sin_clave_de_gemini_el_error_es_claro():
    tarea = resultado_de(subir([txt()]))  # sin el fixture llm → sin GOOGLE_API_KEY
    assert tarea["estado"] == "error" and "no está configurado" in tarea["mensaje"]


def test_endpoint_sincrono_con_el_json_de_la_consigna(llm):
    r = cliente.post("/adaptar/sincrono", json={
        "documento_titulo": "Introduccion a la Arquitectura de Redes VCN en OCI", "documento_contenido": texto_unico(),
        "perfil_destinatario": "Principiante", "formato_salida": "Flashcards", "nicho_sector": "General", "nivel_detalle": "Didactico",
    })
    cuerpo = r.json()
    assert r.status_code == 200 and cuerpo["status"] == "exito"
    assert {"perfil_aplicado", "formato_generado", "tiempo_estimado_estudio_minutos", "conceptos_clave"} <= set(cuerpo["metadatos"])
    assert {"anclaje_fuente_score", "claridad_pedagogica", "observaciones"} <= set(cuerpo["evaluacion_calidad"])
    assert {"bucket", "objeto_id", "status_upload"} <= set(cuerpo["almacenamiento_oci"])
    assert {"frente", "dorso", "pista_didactica"} <= set(cuerpo["contenido_adaptado"]["items"][0])
    assert cuerpo["diagnostico"]["preguntas"] == []


def test_salud():
    assert cliente.get("/salud").json()["estado"] == "ok"