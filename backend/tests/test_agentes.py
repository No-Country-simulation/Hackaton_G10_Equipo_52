import pytest

from app import agents, chunking, ingesta, vectorstore
from app.config import config
from tests.conftest import FakeLLM, texto_unico

PARAMS = {"perfil_destinatario": "Principiante", "formato_salida": "Flashcards", "nicho_sector": "General", "nivel_detalle": "Didactico"}


@pytest.fixture
def doc_id():
    return vectorstore.indexar(chunking.dividir(ingesta.cargar_texto("VCN", texto_unico())))


def test_recuperacion_devuelve_los_fragmentos(doc_id):
    ctx = vectorstore.contexto(doc_id, ["red privada"])
    assert ctx and ctx[0]["id"] == "chunk_000"
    assert vectorstore.recuperar(doc_id, "subredes públicas y privadas", k=1)[0]["id"] == "chunk_000"


def test_indexar_dos_veces_no_duplica(doc_id):
    fragmentos = chunking.dividir(ingesta.cargar_texto("VCN", texto_unico()))
    assert vectorstore.indexar(fragmentos) == vectorstore.indexar(fragmentos)


def test_flujo_normal_una_pasada(doc_id):
    llm = FakeLLM()
    estado = agents.ejecutar_adaptacion(llm, PARAMS, "VCN", doc_id)
    assert estado["anclaje"] >= config.umbral_fidelidad and estado["intentos"] == 1
    assert llm.llamadas == ["GeneracionFlashcards", "Revision"]


def test_reintenta_si_la_fidelidad_es_baja(doc_id):
    llm = FakeLLM(anclajes=[0.4, 0.95])
    estado = agents.ejecutar_adaptacion(llm, PARAMS, "VCN", doc_id)
    assert estado["intentos"] == 2 and llm.llamadas.count("GeneracionFlashcards") == 2


def test_agota_los_reintentos_y_entrega_igual(doc_id):
    estado = agents.ejecutar_adaptacion(FakeLLM(anclajes=[0.1]), PARAMS, "VCN", doc_id)
    assert estado["intentos"] == config.max_reintentos + 1 and estado["anclaje"] < config.umbral_fidelidad


def test_cita_inexistente_penaliza_el_puntaje(doc_id):
    estado = agents.ejecutar_adaptacion(FakeLLM(cita="chunk_999"), PARAMS, "VCN", doc_id)
    assert estado["anclaje"] == 0 and "chunk_999" in estado["observaciones"]


def test_informa_las_etapas_en_orden(doc_id):
    etapas = []
    agents.ejecutar_adaptacion(FakeLLM(), PARAMS, "VCN", doc_id, al_avanzar=etapas.append)
    assert etapas == [2, 3]


@pytest.mark.parametrize("formato,esquema", [("Quiz", "GeneracionQuiz"), ("Tutorial", "GeneracionPasos"), ("Resumen", "GeneracionPasos")])
def test_cada_formato_usa_su_esquema(doc_id, formato, esquema):
    llm = FakeLLM()
    agents.ejecutar_adaptacion(llm, {**PARAMS, "formato_salida": formato}, "VCN", doc_id)
    assert llm.llamadas[0] == esquema


def test_router_envia_el_diagnostico_al_evaluador(doc_id):
    llm = FakeLLM()
    preguntas = agents.ejecutar_diagnostico(llm, doc_id)
    assert len(preguntas) == 5 and llm.llamadas == ["PreguntasGeneradas"]


def test_json_invalido_termina_en_error_amigable(doc_id):
    with pytest.raises(agents.ErrorGeneracion, match="respuesta inválida"):
        agents.ejecutar_adaptacion(FakeLLM(falla=True), PARAMS, "VCN", doc_id)