from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router

load_dotenv()

app = FastAPI(
    title="Telescope Technical Assignment API",
    version="0.1.0",
    description="Processes company data based on user-defined rules.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict this in production, dev only
    # Example for production
    # allow_origins=["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
