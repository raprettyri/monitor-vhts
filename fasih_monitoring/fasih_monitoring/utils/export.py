from io import BytesIO
import pandas as pd

def make_excel(summary, detail, logs, history):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary.to_excel(writer, index=False, sheet_name="REKAP KABUPATEN KOTA")
        detail.to_excel(writer, index=False, sheet_name="DETAIL OPEN")
        logs.to_excel(writer, index=False, sheet_name="LOG UPDATE")
        history.to_excel(writer, index=False, sheet_name="HISTORI STATUS")
        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for column_cells in ws.columns:
                max_len = max((len(str(c.value or "")) for c in column_cells), default=10)
                ws.column_dimensions[column_cells[0].column_letter].width = min(max(max_len + 2, 12), 42)
    buffer.seek(0)
    return buffer.getvalue()
