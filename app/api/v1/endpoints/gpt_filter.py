from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict
from app.core.deps import get_db
from app.schemas.filtered_keywords import (
    FilteredSearchVolumeCreate,
    FilteredCompetitorCreate,
    FilteredSearchVolumeResponse,
    FilteredCompetitorResponse
)
from app.services.gpt_filter import GPTFilterService

router = APIRouter()

@router.post(
    "/filter-search-volume/{analysis_id}",
    response_model=Dict[str, str],
    summary="使用GPT过滤搜索量分析结果",
    description="""
    启动GPT过滤搜索量分析结果的后台任务。
    - 分析前100个权重最高的关键词
    - 使用GPT进行智能分类
    - 异步处理以提高性能
    """,
    response_description="返回任务启动状态"
)
async def filter_search_volume(
    analysis_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """启动GPT过滤搜索量分析结果的后台任务"""
    filter_service = GPTFilterService(db)
    background_tasks.add_task(
        filter_service.filter_search_volume,
        analysis_id
    )
    return {"message": "搜索量分析过滤任务已启动"}

@router.post(
    "/filter-competitors/{analysis_id}",
    response_model=Dict[str, str],
    summary="使用GPT过滤竞争关键词",
    description="""
    启动GPT过滤竞争关键词的后台任务。
    - 智能识别竞争关系
    - 分类竞争类型
    - 异步处理以提高性能
    """,
    response_description="返回任务启动状态"
)
async def filter_competitors(
    analysis_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """启动GPT过滤竞争关键词的后台任务"""
    filter_service = GPTFilterService(db)
    background_tasks.add_task(
        filter_service.filter_competitors,
        analysis_id
    )
    return {"message": "竞争关键词过滤任务已启动"}

@router.get(
    "/filtered-search-volume/{analysis_id}",
    response_model=List[FilteredSearchVolumeResponse],
    summary="获取已过滤的搜索量分析结果",
    description="获取指定分析ID的已过滤搜索量分析结果列表",
    response_description="返回已过滤的搜索量分析结果列表"
)
async def get_filtered_search_volume(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """获取已过滤的搜索量分析结果"""
    filter_service = GPTFilterService(db)
    return filter_service.get_filtered_search_volume(analysis_id)

@router.get(
    "/filtered-competitors/{analysis_id}",
    response_model=List[FilteredCompetitorResponse],
    summary="获取已过滤的竞争关键词",
    description="获取指定分析ID的已过滤竞争关键词列表",
    response_description="返回已过滤的竞争关键词列表"
)
async def get_filtered_competitors(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """获取已过滤的竞争关键词"""
    filter_service = GPTFilterService(db)
    return filter_service.get_filtered_competitors(analysis_id) 