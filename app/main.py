from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from app.core.database import Base, engine
from app.core.logger import logger

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "Welcome to Keyword Analysis API"}

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Keyword Analysis API")
    Base.metadata.create_all(bind=engine)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Keyword Analysis API") 