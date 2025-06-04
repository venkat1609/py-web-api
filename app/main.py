from fastapi import FastAPI
from app.routes import auth, transactions

app = FastAPI()

# Include the authentication router
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
