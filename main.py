from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import requests

load_dotenv()

app = FastAPI()

# Endpoint de prueba para confirmar que el backend responde
@app.get("/ping")
def ping():
    return {"message": "pong"}

# Ejemplo: obtener pauta desde Bubble (simulado)
@app.get("/generar-reporte")
def generar_reporte():
    bubble_api_url = "https://monitorv3.bubbleapps.io/version-test/api/1.1/obj/Audio"
    bubble_token = os.getenv("BUBBLE_API_TOKEN")

    headers = {
        "Authorization": f"Bearer {bubble_token}",
        "Accept": "application/json"
    }

    response = requests.get(bubble_api_url, headers=headers)

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        return JSONResponse(status_code=500, content={"error": str(err)})

    data = response.json()
    return {"mensaje": "Pauta recibida correctamente", "data": data}

# Este bloque hace que Railway escuche en el puerto correcto
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
