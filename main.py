from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
import io
import httpx
import openpyxl
import os

ACRCLOUD_BASE_URL = "https://api-v2.acrcloud.com/api/bm-cs-projects"
ACRCLOUD_BEARER_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI3IiwianRpIjoiNjYwODQwOTYxMzRiNWM5NjljODY2NDMwMGNiZDFjNzllM2NmZjhiODBkN2Q0ZmY4MTMyYTFmN2QzNGI5NTBjMmFmNTk3ODNhMGJlYjRmMzciLCJpYXQiOjE3MzIyMjA3NDcuNzczMjI4LCJuYmYiOjE3MzIyMjA3NDcuNzczMjMxLCJleHAiOjIwNDc3NTM1NDcuNzI2MDMyLCJzdWIiOiIxNTMzMjUiLCJzY29wZXMiOlsiKiIsIndyaXRlLWFsbCIsInJlYWQtYWxsIiwiYnVja2V0cyIsIndyaXRlLWJ1Y2tldHMiLCJyZWFkLWJ1Y2tldHMiLCJhdWRpb3MiLCJ3cml0ZS1hdWRpb3MiLCJyZWFkLWF1ZGlvcyIsImNoYW5uZWxzIiwid3JpdGUtY2hhbm5lbHMiLCJyZWFkLWNoYW5uZWxzIiwiYmFzZS1wcm9qZWN0cyIsIndyaXRlLWJhc2UtcHJvamVjdHMiLCJyZWFkLWJhc2UtcHJvamVjdHMiLCJ1Y2YiLCJ3cml0ZS11Y2YiLCJyZWFkLXVjZiIsImRlbGV0ZS11Y2YiLCJibS1wcm9qZWN0cyIsImJtLWNzLXByb2plY3RzIiwid3JpdGUtYm0tY3MtcHJvamVjdHMiLCJyZWFkLWJtLWNzLXByb2plY3RzIiwiYm0tYmQtcHJvamVjdHMiLCJ3cml0ZS1ibS1iZC1wcm9qZWN0cyIsInJlYWQtYm0tYmQtcHJvamVjdHMiLCJmaWxlc2Nhbm5pbmciLCJ3cml0ZS1maWxlc2Nhbm5pbmciLCJyZWFkLWZpbGVzY2FubmluZyIsIm1ldGFkYXRhIiwicmVhZC1tZXRhZGF0YSJdfQ.b0XSJI7YCgd-AWGCLMdPJWo84470QNqovjtp34TKqrjlrnURCEqoI5jE3pBqqKqkVzh46HQjqtyIj7ge7JbNrEichHClKFIGW-JCrxYk-Oo8iDoWq8u-kCARPUrhAUMB_krK2PkkONN21gN4ZguFXgqBEZg2DwincaZhtDGKlM4MbQ9ctMgGapaHQXGa2SyoBQI9fZdNpQrTIplYznKZ2k8g86_8M9Be-tSpPBFEq0nwCKWF_Ya8USU_lxQUiOmAr4Wo5A0mi2FFeUIY7h4AhgP_LkgOwUMVt2JP95edVLlzUuRRVGkW1BG7536V4K51NOh4zr6tK28dixEQCuMj3nPHNG6w0VsT80yVU8mJTcOKxcjCexJNfwoyyAHRJblx6xsG2IZYECCJM0NFRv9GVMKLp2IUKTYM741HnpIGNowav6sNXsRgM8aVPXghf4jbJwfbuzC6XWD3hnQ0D5ybD-V9wAvkEJ0lIIDdkfrMZLW-bI1ju0oRV2CzFl-NpVRqjRp8tBM--6oq51LPx_qm_6CzZsUC6qQeBc1uFL39g_UbbmR4nT4y9w_ENSq1VDz9t8jDdas2arY8T1YzDQW1unbA2UfsyVc57YD4xjcWSLGrFbceS2SvQkGyqEHtB_riLZhl-x9rt8BCw73aFEu7WfOTOLgPs_y-rwgsVeQcKLc"

app = FastAPI()

class Material(BaseModel):
    acr_id: str
    fechas: list[str]  # formato YYYYMMDD
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
    params = {"date": date, "with_false_positive": 0}
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

def generar_excel(data: list):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte"
    ws.append(["Fecha", "Hora Pautada", "Hora Detectada", "ACR_ID", "Título", "Stream", "Status"])
    for item in data:
        ws.append([
            item["fecha"],
            item["hora_pautada"],
            item.get("hora_detectada", ""),
            item["acr_id"],
            item.get("titulo", ""),
            item["stream"],
            item["status"]
        ])
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

@app.post("/generar-reporte")
async def generar_reporte(payload: ProyectoRequest):
    reporte_final = []

    for material in payload.materiales:
        for fecha in material.fechas:
            for stream_id in material.stream_ids:
                resultado = await get_results_from_acrcloud(payload.proyecto_id, stream_id, fecha)
                if "error" in resultado:
                    return JSONResponse(content=resultado, status_code=500)

                detecciones = resultado.get("data", [])
                coincidencias = []
                ya_reportados = set()

                # Procesar detecciones
                for deteccion in detecciones:
                    for item in deteccion.get("metadata", {}).get("custom_files", []):
                        if item.get("acrid") != material.acr_id:
                            continue

                        # Convertir UTC a hora local (UTC-6 para Guatemala)
                        utc_str = deteccion.get("metadata", {}).get("timestamp_utc", "")
                        dt_utc = datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%S")
                        dt_local = dt_utc - timedelta(hours=6)
                        hora_detectada = dt_local.strftime("%H:%M")

                        # Comparar con cada hora pautada
                        detectado_en_horario = False
                        for hora_pauta in material.horarios:
                            hora_objetivo = datetime.strptime(f"{fecha} {hora_pauta}", "%Y%m%d %H:%M")
                            hora_detectada_dt = datetime.strptime(f"{fecha} {hora_detectada}", "%Y%m%d %H:%M")
                            delta = abs((hora_detectada_dt - hora_objetivo).total_seconds()) / 60
                            if delta <= payload.tolerancia_minutos:
                                detectado_en_horario = True
                                ya_reportados.add((fecha, hora_pauta, stream_id))
                                reporte_final.append({
                                    "fecha": fecha,
                                    "hora_pautada": hora_pauta,
                                    "hora_detectada": hora_detectada,
                                    "acr_id": material.acr_id,
                                    "titulo": item.get("title", ""),
                                    "stream": stream_id,
                                    "status": "DETECTADO"
                                })
                                break

                        if not detectado_en_horario:
                            reporte_final.append({
                                "fecha": fecha,
                                "hora_pautada": "",
                                "hora_detectada": hora_detectada,
                                "acr_id": material.acr_id,
                                "titulo": item.get("title", ""),
                                "stream": stream_id,
                                "status": "FUERA DE HORARIO"
                            })

                # Marcar faltantes
                for hora_pauta in material.horarios:
                    if (fecha, hora_pauta, stream_id) not in ya_reportados:
                        reporte_final.append({
                            "fecha": fecha,
                            "hora_pautada": hora_pauta,
                            "hora_detectada": "",
                            "acr_id": material.acr_id,
                            "titulo": "",
                            "stream": stream_id,
                            "status": "FALTANTE"
                        })

    excel = generar_excel(reporte_final)
    fecha_actual = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"reporte_{fecha_actual}.xlsx"

    return StreamingResponse(excel, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={filename}"})
