
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import os
import pandas as pd
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.post("/subir-proyecto")
async def subir_proyecto(request: Request):
    data = await request.json()
    nombre_proyecto = data.get("nombre", "sin_nombre")
    num_materiales = len(data.get("materiales", []))
    return {
        "status": "ok",
        "mensaje": f"Proyecto {nombre_proyecto} recibido con {num_materiales} materiales."
    }

@app.post("/generar-reporte")
async def generar_reporte(request: Request):
    data = await request.json()

    proyecto_info = {
        "ID Proyecto": data.get("proyecto_id"),
        "Nombre": data.get("nombre"),
        "Cliente": data.get("cliente"),
        "Agencia": data.get("agencia"),
        "Marca": data.get("marca"),
        "Producto": data.get("producto"),
        "Tipo Cliente": data.get("tipo_cliente"),
        "Tolerancia (min)": data.get("tolerancia_minutos"),
        "Reportes": ", ".join(data.get("tipo_reportes", [])),
        "Destinatarios": ", ".join(data.get("destinatarios", [])),
        "Cantidad de materiales": len(data.get("materiales", []))
    }

    materiales_data = []
    for m in data.get("materiales", []):
        for stream_id in m.get("streams", []):
            for fecha in m.get("fechas_activas", []):
                for horario in m.get("horarios", []):
                    materiales_data.append({
                        "Material": m["nombre"],
                        "acr_id": m["acr_id"],
                        "Fecha": fecha,
                        "Hora exacta": horario["hora_exacta"],
                        "Stream ID": stream_id,
                        "Categoría": m.get("categoria"),
                        "Conflictos": ", ".join(m.get("conflicto_con", [])),
                        "Back to back": ", ".join(m.get("back_to_back", []))
                    })

    streams_data = data.get("streams_catalogo", [])

    df_proyecto = pd.DataFrame([proyecto_info])
    df_materiales = pd.DataFrame(materiales_data)
    df_streams = pd.DataFrame(streams_data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_proyecto.to_excel(writer, sheet_name="Proyecto", index=False)
        df_materiales.to_excel(writer, sheet_name="Materiales", index=False)
        df_streams.to_excel(writer, sheet_name="Streams", index=False)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte.xlsx"}
    )
