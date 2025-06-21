import os
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
from datetime import datetime
import httpx
import pandas as pd
from fastapi.responses import FileResponse

load_dotenv()

app = FastAPI()

ACR_TOKEN = os.getenv("ACR_BEARER_TOKEN")

class ReportRequest(BaseModel):
    acr_id: str
    project_id: int
    stream_id: str
    fechas: List[str]  # formato: "20250610"
    horas: List[str]   # formato: "08:45"
    tolerancia_minutos: int

def convertir_a_minutos(hora_str):
    h, m = map(int, hora_str.split(":"))
    return h * 60 + m

@app.post("/generar-reporte")
async def generar_reporte(data: ReportRequest):
    headers = {
        "Authorization": f"Bearer {ACR_TOKEN}",
        "Accept": "application/json"
    }

    pautados = []
    detectados = []

    for fecha in data.fechas:
        url = f"https://api-v2.acrcloud.com/api/bm-cs-projects/{data.project_id}/streams/{data.stream_id}/results"
        params = {"date": fecha, "with_false_positive": 0}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                results = response.json()["data"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al consultar ACRCloud: {e}")

        # Filtrar resultados que coincidan con acr_id
        resultados_filtrados = [
            r for r in results
            if r.get("metadata", {}).get("music", [{}])[0].get("acrid") == data.acr_id
        ]

        resultados_por_minuto = [
            convertir_a_minutos(r["metadata"]["timestamp_utc"][11:16])
            for r in resultados_filtrados
        ]

        for hora_str in data.horas:
            pauta_min = convertir_a_minutos(hora_str)
            encontrado = False
            for resultado_min in resultados_por_minuto:
                if abs(resultado_min - pauta_min) <= data.tolerancia_minutos:
                    encontrado = True
                    break
            registro = {
                "fecha": fecha,
                "hora_pautada": hora_str,
                "estado": "Detectado" if encontrado else "No detectado"
            }
            (detectados if encontrado else pautados).append(registro)

    df = pd.DataFrame(pautados + detectados)
    filename = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = f"/tmp/{filename}"
    df.to_excel(filepath, index=False)

    return FileResponse(filepath, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
