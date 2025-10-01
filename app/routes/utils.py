from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import pytesseract
import io

router = APIRouter()

@router.post("/extract_receipt")
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
