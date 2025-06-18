import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import requests

# Cargar variables de entorno
load_dotenv()

app = FastAPI()

ACR_TOKEN = os.getenv("ACR_TOKEN")
BUBBLE_API_KEY = os.getenv("BUBBLE_API_KEY")

@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.get("/test-acr-token")
def test_acr_token():
    if not ACR_TOKEN:
        raise HTTPException(status_code=500, detail="ACR_TOKEN no está definido")
    return {"ACR_TOKEN": ACR_TOKEN[:4] + "..."}

@app.get("/test-bubble")
def test_bubble_key():
    if not BUBBLE_API_KEY:
        raise HTTPException(status_code=500, detail="BUBBLE_API_KEY no está definido")
    headers = {
        "Authorization": f"Bearer {BUBBLE_API_KEY}"
    }
    try:
        response = requests.get(
            "https://monitorv3.bubbleapps.io/version-test/api/1.1/obj/Audio",
            headers=headers
        )
        response.raise_for_status()
        return {"status": "ok", "count": len(response.json().get("response", {}).get("results", []))}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

# Incluir si corres localmente
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
