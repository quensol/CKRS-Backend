from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.core.deps import get_db
from app.schemas.filtered_keywords import (
    FilteredSearchVolumeCreate,
    FilteredCompetitorCreate,
    FilteredSearchVolumeResponse,
    FilteredCompetitorResponse
)
from app.services.gpt_filter import GPTFilterService
from app.services.gpt_service import GPTService
from app.core.logger import logger
from app import models

router = APIRouter()
gpt_service = GPTService()

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

@router.post("/search-keywords/{analysis_id}",
    response_model=Dict[str, Any],
    summary="GPT过滤搜索关键词",
    description="使用GPT对搜索关键词进行分类过滤"
)
async def filter_search_keywords(
    analysis_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """GPT过滤搜索关键词"""
    try:
        # 检查是否已经过滤过
        existing = db.query(models.FilteredSearchVolumeAnalysis).filter(
            models.FilteredSearchVolumeAnalysis.seed_analysis_id == analysis_id
        ).first()
        
        if existing:
            return {
                "status": "completed",
                "message": "搜索关键词已完成GPT过滤",
                "analysis_id": analysis_id
            }
            
        # 在后台执行过滤任务
        background_tasks.add_task(gpt_service.filter_search_keywords, analysis_id, db)
        
        return {
            "status": "processing",
            "message": "搜索关键词GPT过滤任务已启动",
            "analysis_id": analysis_id
        }
        
    except Exception as e:
        logger.error(f"GPT过滤搜索关键词失败: {str(e)}")
        return {
            "status": "failed",
            "message": f"GPT过滤失败: {str(e)}",
            "analysis_id": analysis_id
        }

@router.post("/competitor-keywords/{analysis_id}",
    response_model=Dict[str, Any],
    summary="GPT过滤竞争关键词",
    description="使用GPT对竞争关键词进行分类过滤"
)
async def filter_competitor_keywords(
    analysis_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """GPT过滤竞争关键词"""
    try:
        # 检查是否已经过滤过
        existing = db.query(models.FilteredCompetitorKeywords).filter(
            models.FilteredCompetitorKeywords.seed_analysis_id == analysis_id
        ).first()
        
        if existing:
            return {
                "status": "completed",
                "message": "竞争关键词已完成GPT过滤",
                "analysis_id": analysis_id
            }
            
        # 在后台执行过滤任务
        background_tasks.add_task(gpt_service.filter_competitor_keywords, analysis_id, db)
        
        return {
            "status": "processing",
            "message": "竞争关键词GPT过滤任务已启动",
            "analysis_id": analysis_id
        }
        
    except Exception as e:
        logger.error(f"GPT过滤竞争关键词失败: {str(e)}")
        return {
            "status": "failed",
            "message": f"GPT过滤失败: {str(e)}",
            "analysis_id": analysis_id
        }

@router.get("/search-keywords/{analysis_id}/status",
    response_model=Dict[str, Any],
    summary="获取搜索关键词过滤状态",
    description="获取GPT搜索关键词过滤的处理状态"
)
async def get_search_keywords_status(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """获取搜索关键词过滤状态"""
    try:
        filtered = db.query(models.FilteredSearchVolumeAnalysis).filter(
            models.FilteredSearchVolumeAnalysis.seed_analysis_id == analysis_id
        ).first()
        
        if filtered:
            return {
                "status": "completed",
                "message": "搜索关键词已完成GPT过滤",
                "analysis_id": analysis_id
            }
        else:
            return {
                "status": "processing",
                "message": "搜索关键词GPT过滤进行中",
                "analysis_id": analysis_id
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取状态失败: {str(e)}",
            "analysis_id": analysis_id
        }

@router.get("/competitor-keywords/{analysis_id}/status",
    response_model=Dict[str, Any],
    summary="获取竞争关键词过滤状态",
    description="获取GPT竞争关键词过滤的处理状态"
)
async def get_competitor_keywords_status(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """获取竞争关键词过滤状态"""
    try:
        filtered = db.query(models.FilteredCompetitorKeywords).filter(
            models.FilteredCompetitorKeywords.seed_analysis_id == analysis_id
        ).first()
        
        if filtered:
            return {
                "status": "completed",
                "message": "竞争关键词已完成GPT过滤",
                "analysis_id": analysis_id
            }
        else:
            return {
                "status": "processing",
                "message": "竞争关键词GPT过滤进行中",
                "analysis_id": analysis_id
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取状态失败: {str(e)}",
            "analysis_id": analysis_id
        }

@router.post("/integrated-analysis/{analysis_id}",
    response_model=Dict[str, Any],
    summary="GPT统合分析",
    description="""
    使用GPT直接对原始数据进行统合分析，包括：
    - 搜索关键词分类
    - 竞争关键词分析
    - 市场洞察生成
    所有分析在一次GPT调用中完成，确保分析的一致性。
    """
)
async def integrated_analysis(
    analysis_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """GPT统合分析"""
    try:
        # 检查分析记录是否存在
        analysis = db.query(models.SeedKeywordAnalysis).filter(
            models.SeedKeywordAnalysis.id == analysis_id
        ).first()
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis ID {analysis_id} not found"
            )
            
        # 检查是否已有统合分析结果
        existing_insight = db.query(models.MarketInsight).filter(
            models.MarketInsight.seed_analysis_id == analysis_id
        ).first()
        
        if existing_insight:
            return {
                "status": "completed",
                "message": "统合分析已完成",
                "analysis_id": analysis_id,
                "insight": existing_insight.content
            }
            
        # 获取原始搜索量数据
        search_volumes = db.query(models.SearchVolumeAnalysis).filter(
            models.SearchVolumeAnalysis.seed_analysis_id == analysis_id
        ).order_by(models.SearchVolumeAnalysis.weight.desc()).limit(100).all()
        
        # 获取原始竞争词数据
        competitors = db.query(models.CompetitorKeyword).filter(
            models.CompetitorKeyword.seed_analysis_id == analysis_id
        ).order_by(models.CompetitorKeyword.weighted_competition_score.desc()).limit(50).all()
        
        # 获取用户画像数据
        profile_stats = db.query(models.UserProfileStatistics).filter(
            models.UserProfileStatistics.seed_analysis_id == analysis_id
        ).first()
        
        profile_dist = db.query(models.UserProfileDistribution).filter(
            models.UserProfileDistribution.seed_analysis_id == analysis_id
        ).all()
        
        # 在后台执行统合分析
        background_tasks.add_task(
            gpt_service.integrated_analysis,
            analysis_id=analysis_id,
            seed_keyword=analysis.seed_keyword,
            search_volumes=search_volumes,
            competitors=competitors,
            profile_stats=profile_stats,
            profile_dist=profile_dist,
            db=db
        )
        
        return {
            "status": "processing",
            "message": "统合分析任务已启动",
            "analysis_id": analysis_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动统合分析失败: {str(e)}")
        return {
            "status": "failed",
            "message": f"启动统合分析失败: {str(e)}",
            "analysis_id": analysis_id
        }

@router.get("/integrated-analysis/{analysis_id}/status",
    response_model=Dict[str, Any],
    summary="获取统合分析状态",
    description="获取GPT统合分析的处理状态和结果"
)
async def get_integrated_analysis_status(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """获取统合分析状态"""
    try:
        insight = db.query(models.MarketInsight).filter(
            models.MarketInsight.seed_analysis_id == analysis_id
        ).first()
        
        if insight:
            return {
                "status": "completed",
                "message": "统合分析已完成",
                "analysis_id": analysis_id,
                "insight": insight.content
            }
        else:
            return {
                "status": "processing",
                "message": "统合分析进行中",
                "analysis_id": analysis_id
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取状态失败: {str(e)}",
            "analysis_id": analysis_id
        } 