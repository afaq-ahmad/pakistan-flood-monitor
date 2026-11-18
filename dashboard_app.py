import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from backend_service import DEMO_WATERMARK
from pakistan_flood_monitor.config import settings

app = FastAPI(title="Pakistan Flood Monitor Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CSV_FILE = os.path.join("data", "mock_flood_data.csv")


def require_demo_mode() -> None:
    if not settings.synthetic_data_allowed:
        raise HTTPException(status_code=503, detail="The standalone dashboard requires demo or test mode.")


@app.get("/api/events", dependencies=[Depends(require_demo_mode)])
def get_events():
    if not os.path.exists(CSV_FILE):
        return {"status": "error", "message": "CSV file not found", "data": []}
    
    try:
        df = pd.read_csv(CSV_FILE)
        # Convert NaN to None for JSON serialization
        df = df.where(pd.notnull(df), None)
        return {
            "status": "success",
            "product_label": "SIMULATED",
            "demo_watermark": DEMO_WATERMARK,
            "data": df.to_dict(orient="records"),
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "data": []}

app.mount("/static", StaticFiles(directory="dashboard"), name="static")

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(require_demo_mode)])
def serve_dashboard():
    dashboard_path = os.path.join("dashboard", "index.html")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    print("Starting Flood Monitor Dashboard on http://127.0.0.1:8002")
    uvicorn.run("dashboard_app:app", host="127.0.0.1", port=8002, reload=True)
