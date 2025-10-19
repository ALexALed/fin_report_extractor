from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from infra.xlsx_reader import XlsxFileReader


@pytest.mark.asyncio
async def test_xlsx_file_reader_merges_docs(monkeypatch):
    test_file = (
        Path(__file__).resolve().parent.parent / "test_data" / "simple_example.xlsx"
    )
    captured = {}
    docs = [
        SimpleNamespace(page_content="First page", metadata={"source": "sheet1"}),
        SimpleNamespace(page_content="Second page", metadata={"author": "bot"}),
    ]

    class LoaderStub:
        def __init__(self, file_path: str, mode: str):
            captured["file_path"] = file_path
            captured["mode"] = mode

        async def aload(self):
            return docs

    monkeypatch.setattr(
        "infra.xlsx_reader.UnstructuredExcelLoader",
        LoaderStub,
    )

    reader = XlsxFileReader()
    result = await reader.read(str(test_file))

    assert captured["file_path"] == str(test_file)
    assert captured["mode"] == "single"
    assert result.content == "First page\n\nSecond page"
    assert result.metadata == {"source": "sheet1", "author": "bot"}


@pytest.mark.asyncio
async def test_xlsx_file_reader_raises_for_empty_loader(monkeypatch):
    class EmptyLoaderStub:
        def __init__(self, *_args, **_kwargs):
            pass

        async def aload(self):
            return []

    monkeypatch.setattr(
        "infra.xlsx_reader.UnstructuredExcelLoader",
        EmptyLoaderStub,
    )
    reader = XlsxFileReader()

    with pytest.raises(ValueError):
        await reader.read("/tmp/does-not-matter.xlsx")


@pytest.mark.asyncio
async def test_structured_output_returns_records(monkeypatch):
    reader = XlsxFileReader()
    dataframe = pd.DataFrame(
        [
            {"account": "Revenue", "amount": 1234.56},
            {"account": "Expense", "amount": 42.0},
        ]
    )
    captured = {}

    def fake_read_excel(path: str):
        captured["path"] = path
        return dataframe

    monkeypatch.setattr("infra.xlsx_reader.pd.read_excel", fake_read_excel)

    result = await reader.structured_output("/tmp/sample.xlsx")

    assert captured["path"] == "/tmp/sample.xlsx"
    assert result == [
        {"account": "Revenue", "amount": 1234.56},
        {"account": "Expense", "amount": 42.0},
    ]
