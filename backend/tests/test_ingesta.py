import io

import pytest
from pypdf import PdfWriter

from app.ingesta import ErrorIngesta, cargar_documento, cargar_texto, limpiar, nombre_seguro
from tests.conftest import TEXTO


def pdf_con_texto(texto: str) -> bytes:
    """PDF mínimo de una página (evita depender de otra librería en los tests)."""
    flujo = f"BT /F1 12 Tf 72 720 Td ({texto}) Tj ET".encode()
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(flujo) + flujo + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    salida, posiciones = b"%PDF-1.4\n", []
    for i, objeto in enumerate(objetos, 1):
        posiciones.append(len(salida))
        salida += b"%d 0 obj\n" % i + objeto + b"\nendobj\n"
    xref = len(salida)
    salida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    salida += b"".join(b"%010d 00000 n \n" % p for p in posiciones)
    return salida + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objetos) + 1, xref)


def test_texto_plano():
    docs = cargar_documento("notas.txt", TEXTO.encode())
    assert docs[0].metadata == {"fuente": "notas.txt", "tipo": "txt"}


def test_markdown_con_latin1():
    docs = cargar_documento("guia.md", ("# Título\n\n" + TEXTO).encode("latin-1"))
    assert docs[0].metadata["tipo"] == "md" and "Título" in docs[0].page_content


def test_pdf_lee_pagina_por_pagina():
    docs = cargar_documento("manual.pdf", pdf_con_texto("VCN es una red privada en la nube de Oracle y permite controlar el trafico"))
    assert docs[0].metadata["pagina"] == 1 and "VCN" in docs[0].page_content


def test_texto_pegado():
    assert cargar_texto("Mi doc", TEXTO)[0].metadata["fuente"] == "Mi doc"


@pytest.mark.parametrize("nombre,datos,fragmento", [
    ("a.txt", b"", "vacío"),
    ("a.docx", b"datos", "formato no soportado"),
    ("a.txt", b"corto", "extraer texto"),
    ("a.pdf", b"no soy un pdf", "dañado"),
])
def test_errores_amigables(nombre, datos, fragmento):
    with pytest.raises(ErrorIngesta, match=fragmento):
        cargar_documento(nombre, datos)


def test_pdf_sin_texto_se_avisa():
    escritor, buffer = PdfWriter(), io.BytesIO()
    escritor.add_blank_page(100, 100)
    escritor.write(buffer)
    with pytest.raises(ErrorIngesta, match="PDF escaneado"):
        cargar_documento("escaneado.pdf", buffer.getvalue())


def test_nombre_seguro_evita_rutas():
    assert nombre_seguro("../../etc/passwd") == "passwd"
    assert nombre_seguro("C:\\x\\mi archivo<1>.pdf") == "mi archivo_1_.pdf"
    assert nombre_seguro(None) == "documento"


def test_limpieza_une_palabras_cortadas():
    assert limpiar("informa-\nción  útil\n\n\n\nfin") == "información útil\n\nfin"