import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from typing import List
from datetime import datetime, timedelta
import pandas as pd
import io
import httpx

app = FastAPI()

ACRCLOUD_BASE_URL = "https://api.acrcloud.com/v1/monitor-streams"
BEARER_TOKEN = "TU_BEARER_TOKEN_AQUI"

class Material(BaseModel):
    acr_id: str
    fechas_activas: List[str]
    horarios: List[str]
    stream_id: str
    categoria: str
    conflictos: List[str]

class ProyectoRequest(BaseModel):
    proyecto_id: int
    nombre: str
    cliente: str
    tipo_cliente: str
    tolerancia_minutos: int
    tipos_reporte: List[str]
    destinatarios: List[EmailStr]
    materiales: List[Material]
    streams_catalogo: dict

@app.post("/generar-reporte")
async def generar_reporte(request: ProyectoRequest):
    filas_excel = []

    async with httpx.AsyncClient() as client:
        for material in request.materiales:
            for fecha_str in material.fechas_activas:
                fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                inicio = fecha_dt.replace(hour=0, minute=0, second=0)
                fin = fecha_dt.replace(hour=23, minute=59, second=59)

                inicio_str = inicio.strftime("%Y-%m-%dT%H:%M:%SZ")
                fin_str = fin.strftime("%Y-%m-%dT%H:%M:%SZ")

                url = f"{ACRCLOUD_BASE_URL}/{request.proyecto_id}/streams/{material.stream_id}/results"
                headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
                params = {
                    "start_time": inicio_str,
                    "end_time": fin_str
                }

                response = await client.get(url, headers=headers, params=params)
                data = response.json()

                detecciones = []
                for item in data.get("data", []):
                    for detected in item.get("metadata", {}).get("custom_files", []):
                        detecciones.append({
                            "acrid": detected.get("acrid"),
                            "hora_detectada": datetime.strptime(item["metadata"]["timestamp_utc"], "%Y-%m-%d %H:%M:%S").time()
                        })

                for hora_str in material.horarios:
                    hora_obj = datetime.strptime(hora_str, "%H:%M").time()
                    hora_min = (datetime.combine(fecha_dt, hora_obj) - timedelta(minutes=request.tolerancia_minutos)).time()
                    hora_max = (datetime.combine(fecha_dt, hora_obj) + timedelta(minutes=request.tolerancia_minutos)).time()

                    detectado = any(
                        d["acrid"] == material.acr_id and hora_min <= d["hora_detectada"] <= hora_max
                        for d in detecciones
                    )

                    filas_excel.append({
                        "Fecha": fecha_str,
                        "Hora programada": hora_str,
                        "Stream": material.stream_id,
                        "ACR ID": material.acr_id,
                        "Detectado": "Sí" if detectado else "No"
                    })

    df = pd.DataFrame(filas_excel)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Reporte")
    output.seek(0)

    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=acrcloud_reporte.xlsx"})
