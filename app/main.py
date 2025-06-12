from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, transactions, categories
from fastapi.responses import JSONResponse
from datetime import datetime
from PIL import Image
import pytesseract
import io
from app.scheduler import start_scheduler


app = FastAPI()

# Allow CORS for your frontend domain
origins = ["http://localhost:3000", "https://gowisely.netlify.app"]  # React dev server

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Or use ["*"] to allow all (not recommended for prod)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    start_scheduler()
    print("Scheduler started.")


@app.get("/health")
async def health_check():
    return JSONResponse(
        content={"status": "ok", "timestamp": datetime.utcnow().isoformat()},
        status_code=200,
    )


# Set tesseract path on Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


@app.post("/extract-receipt")
async def extract_receipt(image: UploadFile = File(...)):
    if image.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(
            status_code=400, detail="Only JPEG and PNG files are supported."
        )

    # Read image from upload
    image_bytes = await image.read()
    img = Image.open(io.BytesIO(image_bytes))

    # Extract text with pytesseract
    try:
        text = pytesseract.image_to_string(img)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content={"raw_text": text})


# Include the authentication router
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(categories.router, prefix="/categories", tags=["categories"])
