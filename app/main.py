from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, transactions, categories

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

# Include the authentication router
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(categories.router, prefix="/categories", tags=["categories"])
