from fastapi import FastAPI
from app.routes import auth

app = FastAPI()

# Include the authentication router
app.include_router(auth.router, prefix="/auth", tags=["auth"])
