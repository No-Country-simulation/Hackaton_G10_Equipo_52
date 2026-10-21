import pytest
from langchain_core.documents import Document

from app.chunking import dividir
from app.config import config
from app.ingesta import ErrorIngesta


def test_ids_estables_y_tamano():
    frags = dividir([Document(page_content="palabra " * 600, metadata={"fuente": "a.txt", "tipo": "txt"})])
    assert len(frags) > 1
    assert [f.metadata["chunk_id"] for f in frags[:2]] == ["chunk_000", "chunk_001"]
    assert all(len(f.page_content) <= config.chunk_size for f in frags)
    assert all(f.metadata["fuente"] == "a.txt" for f in frags)


def test_markdown_conserva_la_seccion():
    md = "# Redes\n\nIntroducción a las redes.\n\n## Subredes\n\nLas subredes dividen la red en partes."
    frags = dividir([Document(page_content=md, metadata={"fuente": "a.md", "tipo": "md"})])
    assert "Redes > Subredes" in {f.metadata["seccion"] for f in frags}


def test_documento_demasiado_extenso(monkeypatch):
    monkeypatch.setattr(config, "max_chunks", 2)
    with pytest.raises(ErrorIngesta, match="demasiado extenso"):
        dividir([Document(page_content="palabra " * 2000, metadata={"fuente": "a.txt", "tipo": "txt"})])