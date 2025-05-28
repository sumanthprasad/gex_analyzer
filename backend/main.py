from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
from gex_logic import process_all
import io

app = FastAPI()

# Enable frontend access from localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_excel_with_strike_detection(content_bytes: bytes) -> pd.DataFrame:
    # Try different rows until 'Strike Price' is found
    for skip in range(10):  # Try skipping 0–9 rows
        df = pd.read_excel(io.BytesIO(content_bytes), engine="openpyxl", skiprows=skip)
        if any("strike" in col.lower() for col in df.columns if isinstance(col, str)):
            return df
    raise ValueError("No 'Strike Price' column found in first 10 rows.")

@app.post("/compute")
async def compute(
    file: UploadFile = Form(...),
    spot: float = Form(...),
    strikes: int = Form(...),
    contractSize: int = Form(...),
    vol: float = Form(...),
    expiry: float = Form(...),
    columnMode: str = Form("keyword")
):
    content = await file.read()

    if file.filename.endswith(('.xls', '.xlsx')):
        df = load_excel_with_strike_detection(content)
    else:
        df = pd.read_csv(io.StringIO(content.decode("utf-8")))

    result = process_all(df, spot, strikes, contractSize, vol, expiry, columnMode)
    return JSONResponse(content=result)
