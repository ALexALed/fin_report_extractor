import asyncio
from typing import Any

import pandas as pd
from langchain_community.document_loaders import UnstructuredExcelLoader

from core.fin_report_file_loaders.models import ReportFileData
from core.fin_report_file_loaders.services import ReportFileReader


class XlsxFileReader(ReportFileReader):
    async def read(self, file_path: str) -> ReportFileData | Exception:
        loader = UnstructuredExcelLoader(file_path, mode="single")
        docs = await loader.aload()
        if not docs:
            raise ValueError("No content found in the Excel file.")

        content = "\n\n".join([doc.page_content for doc in docs])
        metadata = {}
        for doc in docs:
            metadata.update(doc.metadata)

        return ReportFileData(content=content, metadata=metadata)

    async def structured_output(self, file_path: str) -> list[dict[str, Any]]:
        excel_data_df = await asyncio.to_thread(pd.read_excel, file_path)
        return excel_data_df.to_dict(orient="records")
