from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.routes import (
    payments,
    auth,
    users,
    transactions,
    categories,
    exchange_rates,
    subscriptions,
    connections,
    loans,
    utils
)
from fastapi.responses import JSONResponse
from datetime import datetime
from PIL import Image
import pytesseract
import io
from app.scheduler import start_scheduler


app = FastAPI()

# Allow CORS for your frontend domain
origins = [
    "http://localhost:3000",
    "https://www.budiee.com",
    "https://budiee.netlify.app",
    "https://preview--grow-your-groceries.lovable.app",
    "https://grow-your-groceries.lovable.app",
]

# React dev server
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



# Include the authentication router
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(categories.router, prefix="/categories", tags=["categories"])
app.include_router(
    exchange_rates.router, prefix="/exchange_rates", tags=["exchange_rates"]
)
app.include_router(
    subscriptions.router, prefix="/subscriptions", tags=["subscriptions"]
)
app.include_router(connections.router, prefix="/connections", tags=["connections"])
app.include_router(loans.router, prefix="/loans", tags=["loans"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])
app.include_router(utils.router, prefix="/utils", tags=["utils"])
