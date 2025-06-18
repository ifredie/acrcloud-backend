import os
import json
import datetime
import requests
import pandas as pd
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse

app = FastAPI()

# Configuración
PID = os.getenv("ACRCLOUD_PROJECT_ID", "TU_PROJECT_ID")
BEARER_TOKEN = os.getenv("ACRCLOUD_BEARER_TOKEN", "TU_BEARER_TOKEN")


@app.post("/subir-pauta")
async def subir_pauta(pauta: UploadFile = File(...)):
    contenido = await pauta.read()
    with open("pauta.json", "wb") as f:
        f.write(contenido)
    return {"mensaje": "Pauta guardada correctamente"}


def consultar_acrcloud_stream(stream_id, fecha_iso):
    url = f"https://api-v2.acrcloud.com/api/bm-cs-projects/{PID}/streams/{stream_id}/results?date={fecha_iso}"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    response = requests.get(url, headers=headers)
    return response.json()


@app.get("/generar-reporte")
def generar_reporte():
    if not os.path.exists("pauta.json"):
        return {"error": "No se ha subido una pauta aún"}

    with open("pauta.json", "r") as f:
        pauta = json.load(f)

    hoy = datetime.date.today().isoformat()
    resultados = []

    for material in pauta["materiales"]:
        acr_id = material["acr_id"]
        fechas_activas = material["fechas_activas"]
        horarios = [h["hora_exacta"] for h in material["horarios"]]
        streams = material["streams"]

        for stream in streams:
            detecciones = consultar_acrcloud_stream(stream, hoy)
            hits = detecciones.get("hits", [])
            for hit in hits:
                resultado = {
                    "material": material["nombre"],
                    "acr_id": acr_id,
                    "stream_id": stream,
                    "timestamp": hit.get("timestamp_utc", ""),
                    "score": hit.get("score", ""),
                    "track_id": hit.get("track_id", ""),
                }
                resultados.append(resultado)

    df = pd.DataFrame(resultados)
    archivo = "reporte.xlsx"
    df.to_excel(archivo, index=False)

    return FileResponse(
        path=archivo,
        filename=archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
