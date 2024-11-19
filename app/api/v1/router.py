from fastapi import APIRouter
from app.api.v1.endpoints import keyword

api_router = APIRouter()
api_router.include_router(keyword.router, prefix="/keyword", tags=["keyword"]) 