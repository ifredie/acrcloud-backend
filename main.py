from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
import io
import httpx
import openpyxl
from collections import defaultdict

ACRCLOUD_BASE_URL = "https://api-v2.acrcloud.com/api/bm-cs-projects"
ACRCLOUD_BEARER_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI3IiwianRpIjoiNjYwODQwOTYxMzRiNWM5NjljODY2NDMwMGNiZDFjNzllM2NmZjhiODBkN2Q0ZmY4MTMyYTFmN2QzNGI5NTBjMmFmNTk3ODNhMGJlYjRmMzciLCJpYXQiOjE3MzIyMjA3NDcuNzczMjI4LCJuYmYiOjE3MzIyMjA3NDcuNzczMjMxLCJleHAiOjIwNDc3NTM1NDcuNzI2MDMyLCJzdWIiOiIxNTMzMjUiLCJzY29wZXMiOlsiKiIsIndyaXRlLWFsbCIsInJlYWQtYWxsIiwiYnVja2V0cyIsIndyaXRlLWJ1Y2tldHMiLCJyZWFkLWJ1Y2tldHMiLCJhdWRpb3MiLCJ3cml0ZS1hdWRpb3MiLCJyZWFkLWF1ZGlvcyIsImNoYW5uZWxzIiwid3JpdGUtY2hhbm5lbHMiLCJyZWFkLWNoYW5uZWxzIiwiYmFzZS1wcm9qZWN0cyIsIndyaXRlLWJhc2UtcHJvamVjdHMiLCJyZWFkLWJhc2UtcHJvamVjdHMiLCJ1Y2YiLCJ3cml0ZS11Y2YiLCJyZWFkLXVjZiIsImRlbGV0ZS11Y2YiLCJibS1wcm9qZWN0cyIsImJtLWNzLXByb2plY3RzIiwid3JpdGUtYm0tY3MtcHJvamVjdHMiLCJyZWFkLWJtLWNzLXByb2plY3RzIiwiYm0tYmQtcHJvamVjdHMiLCJ3cml0ZS1ibS1iZC1wcm9qZWN0cyIsInJlYWQtYm0tYmQtcHJvamVjdHMiLCJmaWxlc2Nhbm5pbmciLCJ3cml0ZS1maWxlc2Nhbm5pbmciLCJyZWFkLWZpbGVzY2FubmluZyIsIm1ldGFkYXRhIiwicmVhZC1tZXRhZGF0YSJdfQ.b0XSJI7YCgd-AWGCLMdPJWo84470QNqovjtp34TKqrjlrnURCEqoI5jE3pBqqKqkVzh46HQjqtyIj7ge7JbNrEichHClKFIGW-JCrxYk-Oo8iDoWq8u-kCARPUrhAUMB_krK2PkkONN21gN4ZguFXgqBEZg2DwincaZhtDGKlM4MbQ9ctMgGapaHQXGa2SyoBQI9fZdNpQrTIplYznKZ2k8g86_8M9Be-tSpPBFEq0nwCKWF_Ya8USU_lxQUiOmAr4Wo5A0mi2FFeUIY7h4AhgP_LkgOwUMVt2JP95edVLlzUuRRVGkW1BG7536V4K51NOh4zr6tK28dixEQCuMj3nPHNG6w0VsT80yVU8mJTcOKxcjCexJNfwoyyAHRJblx6xsG2IZYECCJM0NFRv9GVMKLp2IUKTYM741HnpIGNowav6sNXsRgM8aVPXghf4jbJwfbuzC6XWD3hnQ0D5ybD-V9wAvkEJ0lIIDdkfrMZLW-bI1ju0oRV2CzFl-NpVRqjRp8tBM--6oq51LPx_qm_6CzZsUC6qQeBc1uFL39g_UbbmR4nT4y9w_ENSq1VDz9t8jDdas2arY8T1YzDQW1unbA2UfsyVc57YD4xjcWSLGrFbceS2SvQkGyqEHtB_riLZhl-x9rt8BCw73aFEu7WfOTOLgPs_y-rwgsVeQcKLc"

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
            return {"error": response.text, "codigo": response.status_code, "detalle": f"Error en stream {stream_id} con fecha {date}"}

def generar_resumen(detectados, faltantes):
    conteo = defaultdict(lambda: defaultdict(lambda: {"Detectados": 0, "Faltantes": 0}))

    for r in detectados:
        conteo[r["fecha"]][r["stream"]]["Detectados"] += 1

    for r in faltantes:
        conteo[r["fecha"]][r["stream"]]["Faltantes"] += 1

    resumen = []
    total_detectados = 0
    total_faltantes = 0

    for fecha in sorted(conteo.keys()):
        for stream in sorted(conteo[fecha].keys()):
            detect = conteo[fecha][stream]["Detectados"]
            falt = conteo[fecha][stream]["Faltantes"]
            resumen.append([fecha, stream, detect, falt])
            total_detectados += detect
            total_faltantes += falt

    resumen.append(["", "TOTAL GENERAL", total_detectados, total_faltantes])
    return resumen

def generar_excel(data: dict):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resultados"
    ws.append(["Fecha", "Hora Detectada", "Hora Pautada", "ACR_ID", "Título", "Stream", "Estado"])

    for item in data.get("detected", []):
        ws.append([
            item["fecha"],
            item["hora"],
            item["hora_pautada"],
            item["acr_id"],
            item["titulo"],
            item["stream"],
            item["estado"]
        ])

    for item in data.get("faltantes", []):
        ws.append([
            item["fecha"],
            "",
            item["hora_pautada"],
            item["acr_id"],
            "FALTANTE",
            item["stream"],
            "FALTANTE"
        ])

    # Nueva hoja de resumen
    resumen_data = generar_resumen(data.get("detected", []), data.get("faltantes", []))
    ws_resumen = wb.create_sheet("Resumen")
    ws_resumen.append(["Fecha", "Stream", "Detectados", "Faltantes"])
    for fila in resumen_data:
        ws_resumen.append(fila)

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
                fecha_formateada = fecha.replace("-", "")
                resultado = await get_results_from_acrcloud(
                    payload.proyecto_id,
                    stream_id,
                    fecha_formateada
                )
                if "error" in resultado:
                    return JSONResponse(content=resultado, status_code=500)

                for deteccion in resultado.get("data", []):
                    for item in deteccion.get("metadata", {}).get("custom_files", []):
                        if item.get("acrid") == material.acr_id:
                            timestamp_utc = deteccion.get("metadata", {}).get("timestamp_utc", "")
                            try:
                                dt_utc = datetime.strptime(timestamp_utc, "%Y-%m-%d %H:%M:%S")
                                dt_local = dt_utc - timedelta(hours=6)
                                hora_local = dt_local.strftime("%H:%M")
                                fecha_local = dt_local.strftime("%Y-%m-%d")
                            except:
                                hora_local = ""
                                fecha_local = fecha

                            resultados.append({
                                "fecha": fecha_local,
                                "hora": hora_local,
                                "acr_id": material.acr_id,
                                "titulo": item.get("title", ""),
                                "stream": stream_id
                            })

    faltantes = []
    resultados_finales = []

    for material in payload.materiales:
        for stream_id in material.stream_ids:
            for fecha in material.fechas:
                for hora in material.horarios:
                    hora_objetivo_dt = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
                    detectado = None

                    for r in resultados:
                        if r["acr_id"] == material.acr_id and r["stream"] == stream_id:
                            hora_detectada_dt = datetime.strptime(f"{r['fecha']} {r['hora']}", "%Y-%m-%d %H:%M")
                            diferencia = abs((hora_detectada_dt - hora_objetivo_dt).total_seconds())

                            if diferencia <= payload.tolerancia_minutos * 60:
                                detectado = {
                                    **r,
                                    "hora_pautada": hora,
                                    "estado": "DETECTADO"
                                }
                                break
                            elif diferencia <= 3600:  # tolerancia extendida 1 hora
                                detectado = {
                                    **r,
                                    "hora_pautada": hora,
                                    "estado": "FUERA DE HORARIO"
                                }

                    if detectado:
                        resultados_finales.append(detectado)
                    else:
                        faltantes.append({
                            "fecha": fecha,
                            "hora_pautada": hora,
                            "acr_id": material.acr_id,
                            "stream": stream_id
                        })

    excel = generar_excel({"detected": resultados_finales, "faltantes": faltantes})
    fecha_actual = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"reporte_{fecha_actual}.xlsx"

    return StreamingResponse(
        excel,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
