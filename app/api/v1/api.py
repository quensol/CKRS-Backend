from fastapi import APIRouter
from app.api.v1.endpoints import keyword, gpt_filter

api_router = APIRouter()
api_router.include_router(keyword.router, prefix="/keyword", tags=["keyword"])
api_router.include_router(gpt_filter.router, prefix="/gpt-filter", tags=["gpt-filter"]) 