import pytest
from pydantic import ValidationError

from app.fidelidad import combinar, verificar_citas
from app.schemas import ItemPaso, ItemQuiz, Parametros, SolicitudAdaptacion


def test_verificar_citas_descarta_inexistentes():
    items = [ItemPaso(titulo_paso="Paso uno", texto="texto", fuentes=["chunk_000", "chunk_999"]),
             ItemPaso(titulo_paso="Paso dos", texto="texto", fuentes=[])]
    proporcion, invalidas = verificar_citas(items, {"chunk_000"})
    assert proporcion == 0.5 and invalidas == ["chunk_999"] and items[0].fuentes == ["chunk_000"]


def test_combinar_penaliza_y_acota():
    assert combinar(0.9, 1.0) == 0.9
    assert combinar(0.9, 0.5) == 0.45
    assert combinar(1.5, 1.0) == 1.0 and combinar(-1, 1.0) == 0.0


def test_quiz_rechaza_respuesta_fuera_de_rango():
    with pytest.raises(ValidationError):
        ItemQuiz(pregunta="¿Qué es?", opciones=["a", "b"], respuesta_correcta=5, justificacion="x")


def test_parametros_aceptan_tildes_y_mayusculas():
    p = Parametros(perfil_destinatario="principiante", formato_salida="FLASHCARDS", nicho_sector="Educación")
    assert (p.perfil_destinatario, p.formato_salida, p.nicho_sector, p.nivel_detalle) == ("Principiante", "Flashcards", "Educacion", "Didactico")


def test_parametros_rechazan_valores_desconocidos():
    with pytest.raises(ValidationError):
        Parametros(perfil_destinatario="Experto", formato_salida="Quiz")


def test_solicitud_de_la_consigna():
    s = SolicitudAdaptacion(
        documento_titulo="Introduccion a la Arquitectura de Redes VCN en OCI", documento_contenido="x" * 60,
        perfil_destinatario="Principiante", formato_salida="Flashcards", nicho_sector="General", nivel_detalle="Didactico",
    )
    assert s.formato_salida == "Flashcards"