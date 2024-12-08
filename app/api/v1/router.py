from fastapi import APIRouter
from app.api.v1.endpoints import keyword, websocket

api_router = APIRouter()
api_router.include_router(keyword.router, prefix="/keyword", tags=["keyword"])
api_router.include_router(websocket.router, prefix="/keyword", tags=["keyword"]) 