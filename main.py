from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, EmailStr, constr
from typing import List, Literal, Optional
import pandas as pd
import io
import requests
import os

app = FastAPI()

# --- Modelos estrictos ---
class Horario(BaseModel):
    hora_exacta: constr(pattern=r"^\d{2}:\d{2}$")

class Material(BaseModel):
    nombre: str
    acr_id: str
    fechas_activas: List[constr(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    horarios: List[Horario]
    streams: List[str]
    categoria: Optional[str]
    conflicto_con: Optional[List[str]]
    back_to_back: Optional[List[str]]

class Stream(BaseModel):
    stream_id: str
    nombre: str
    url_stream: str

class Proyecto(BaseModel):
    proyecto_id: str
    nombre: str
    cliente: str
    agencia: Optional[str]
    marca: Optional[str]
    producto: Optional[str]
    tipo_cliente: Literal["cliente_directo", "agencia"]
    tolerancia_minutos: int
    tipo_reportes: List[Literal["diario", "total"]]
    destinatarios: List[EmailStr]
    materiales: List[Material]
    streams_catalogo: List[Stream]

# --- Utilidad para consultar ACRCloud ---
def obtener_resultados_acrcloud(acr_id: str, bearer_token: str):
    headers = {
        "Authorization": f"Bearer {bearer_token}"
    }
    url = f"https://api.acrcloud.com/v1/analytics/{acr_id}/results"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=502, detail="Error al consultar ACRCloud")

# --- Endpoint principal ---
@app.post("/generar-reporte")
async def generar_reporte(data: Proyecto, request: Request):
    token = os.getenv("ACR_BEARER_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="Token ACRCloud no configurado")

    report_data = []

    for material in data.materiales:
        try:
            resultados = obtener_resultados_acrcloud(material.acr_id, token)
        except HTTPException as e:
            raise e

        for resultado in resultados.get("data", []):
            fecha = resultado.get("play_date", "")
            hora_detectada = resultado.get("play_time", "")
            stream_id = resultado.get("stream_id", "")

            report_data.append({
                "Proyecto": data.nombre,
                "Cliente": data.cliente,
                "Material": material.nombre,
                "Fecha Detectada": fecha,
                "Hora Detectada": hora_detectada,
                "Stream ID": stream_id,
                "Categoría": material.categoria or "",
            })

    df = pd.DataFrame(report_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Reporte")
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_acrcloud.xlsx"}
    )
