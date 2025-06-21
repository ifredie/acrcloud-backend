from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime
import io
import httpx
import openpyxl
import os

ACRCLOUD_BASE_URL = "https://api-v2.acrcloud.com/api/bm-cs-projects"
ACRCLOUD_BEARER_TOKEN = os.getenv("ACRCLOUD_BEARER_TOKEN", "AQUI_VA_TU_TOKEN")  # Reemplaza si no usas env vars

app = FastAPI()

class Material(BaseModel):
    acr_id: str
    fechas: list[str]  # formato YYYY-MM-DD
    horarios: list[str]  # formato HH:MM
    stream_ids: list[str]
    categoria: str
    conflictos: list[str] = []

class ProyectoRequest(BaseModel):
    proyecto_id: str
    cliente: str
    marca: str
    producto: str
    tipo_cliente: str
    tolerancia_minutos: int
    tipo_reporte: list[str]
    destinatarios: list[str]
    materiales: list[Material]
    catalogo_streams: dict

async def get_results_from_acrcloud(project_id: str, stream_id: str, date: str):
    url = f"{ACRCLOUD_BASE_URL}/{project_id}/streams/{stream_id}/results"
    params = {
        "date": date,
        "with_false_positive": 0
    }
    headers = {
        "Authorization": f"Bearer {ACRCLOUD_BEARER_TOKEN}",
        "Accept": "application/json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.text}

def generar_excel(data: dict):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resultados"
    ws.append(["Fecha", "Hora", "ACR_ID", "Título", "Stream"])

    for item in data.get("detected", []):
        ws.append([
            item["fecha"],
            item["hora"],
            item["acr_id"],
            item["titulo"],
            item["stream"]
        ])

    for item in data.get("faltantes", []):
        ws.append([
            item["fecha"],
            item["hora"],
            item["acr_id"],
            "FALTANTE",
            item["stream"]
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

@app.post("/generar-reporte")
async def generar_reporte(payload: ProyectoRequest):
    resultados = []
    for material in payload.materiales:
        for stream_id in material.stream_ids:
            for fecha in material.fechas:
                resultado = await get_results_from_acrcloud(
                    payload.proyecto_id,
                    stream_id,
                    fecha
                )
                if "error" in resultado:
                    return JSONResponse(content=resultado, status_code=500)

                try:
                    for deteccion in resultado.get("data", []):
                        metadata = deteccion.get("metadata", {})
                        timestamp = metadata.get("timestamp_utc", "")
                        hora = timestamp[11:16] if len(timestamp) >= 16 else ""

                        for item in metadata.get("custom_files", []):
                            if item.get("acrid") == material.acr_id:
                                resultados.append({
                                    "fecha": fecha,
                                    "hora": hora,
                                    "acr_id": material.acr_id,
                                    "titulo": item.get("title", ""),
                                    "stream": stream_id
                                })
                except Exception as e:
                    return JSONResponse(
                        status_code=500,
                        content={"error": f"Error procesando datos de ACRCloud: {str(e)}"}
                    )

    faltantes = []
    for material in payload.materiales:
        for fecha in material.fechas:
            for hora in material.horarios:
                for stream_id in material.stream_ids:
                    encontrado = any(
                        r["fecha"] == fecha and r["hora"] == hora and
                        r["acr_id"] == material.acr_id and r["stream"] == stream_id
                        for r in resultados
                    )
                    if not encontrado:
                        faltantes.append({
                            "fecha": fecha,
                            "hora": hora,
                            "acr_id": material.acr_id,
                            "stream": stream_id
                        })

    excel = generar_excel({"detected": resultados, "faltantes": faltantes})
    fecha_actual = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"reporte_{fecha_actual}.xlsx"

    return StreamingResponse(
        excel,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
