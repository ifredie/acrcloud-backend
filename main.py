from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import pandas as pd
from io import BytesIO

app = FastAPI()

@app.post("/generar-reporte")
async def generar_reporte(request: Request):
    body = await request.json()
    materiales = body.get("materiales", [])
    streams_catalogo = {s["stream_id"]: s["nombre"] for s in body.get("streams_catalogo", [])}

    rows = []
    for material in materiales:
        for fecha in material.get("fechas_activas", []):
            for horario in material.get("horarios", []):
                for stream_id in material.get("streams", []):
                    rows.append({
                        "Proyecto": body.get("nombre"),
                        "Cliente": body.get("cliente"),
                        "Agencia": body.get("agencia"),
                        "Marca": body.get("marca"),
                        "Producto": body.get("producto"),
                        "Material": material.get("nombre"),
                        "Fecha": fecha,
                        "Hora esperada": horario.get("hora_exacta"),
                        "Emisora": streams_catalogo.get(stream_id, stream_id),
                        "Categoría": material.get("categoria"),
                        "Conflictos": ", ".join(material.get("conflicto_con", [])),
                        "Back-to-back": ", ".join(material.get("back_to_back", []))
                    })

    df = pd.DataFrame(rows)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Reporte")

    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={
        "Content-Disposition": "attachment; filename=reporte.xlsx"
    })
