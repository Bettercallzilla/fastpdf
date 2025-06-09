import os
import uuid
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pdf2image import convert_from_path
import pytesseract
import requests
from concurrent.futures import ProcessPoolExecutor

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def ocr_image(img):
    return pytesseract.image_to_string(img, config="--psm 6")

def process_pdf(file_path):
    images = convert_from_path(file_path, dpi=150)
    with ProcessPoolExecutor() as executor:
        results = executor.map(ocr_image, images)
    return "\n".join(results)

@app.post("/ocr/file")
async def ocr_from_file(file: UploadFile = File(...)):
    filename = f"{uuid.uuid4().hex}.pdf"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    try:
        text = process_pdf(file_path)
        return {"text": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/ocr/url")
async def ocr_from_url(request: Request):
    data = await request.json()
    url = data.get("url")
    if not url:
        return JSONResponse(status_code=400, content={"error": "No URL provided."})

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        filename = f"{uuid.uuid4().hex}.pdf"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(response.content)

        text = process_pdf(file_path)
        return {"text": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
