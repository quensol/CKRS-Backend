from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.logger import logger
from app.schemas.keyword import (
    AnalysisBrief,
    Cooccurrence,
    SearchVolume,
    Competitor,
    AnalysisDetail,
    UserProfileStats,
    UserProfileDist
)
from app.crud.keyword import (
    create_analysis,
    get_analysis,
    get_analyses,
    get_competitors,
    get_cooccurrence,
    get_search_volume
)
from app import models
from app.core.database import get_db
from app.utils.analyzer import run_analysis
import os
from app.services.gpt_service import GPTService

router = APIRouter()

# 创建GPT服务实例
gpt_service = GPTService()

@router.post("/analyze", response_model=AnalysisBrief)
async def analyze_keyword(
    keyword: str,
    db: Session = Depends(get_db)
):
    """创建新的分析任务"""
    try:
        # 检查是否存在已完成的分析
        existing_analysis = db.query(models.SeedKeywordAnalysis).filter(
            models.SeedKeywordAnalysis.seed_keyword == keyword,
            models.SeedKeywordAnalysis.status == "completed"
        ).first()
        
        if existing_analysis:
            return existing_analysis
            
        # 检查是否存在正在处理的分析
        processing_analysis = db.query(models.SeedKeywordAnalysis).filter(
            models.SeedKeywordAnalysis.seed_keyword == keyword,
            models.SeedKeywordAnalysis.status.in_(["pending", "processing"])
        ).first()
        
        if processing_analysis:
            return processing_analysis
        
        # 创建新的分析记录
        analysis_result = {
            "seed_keyword": keyword,
            "status": "pending",
            "total_search_volume": 0,
            "seed_search_volume": 0,
            "seed_search_ratio": 0
        }
        db_analysis = create_analysis(db, analysis_result)
        return db_analysis
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/start-analysis/{analysis_id}", response_model=AnalysisBrief)
async def start_analysis(
    analysis_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """启动分析任务"""
    analysis = db.query(models.SeedKeywordAnalysis).filter(
        models.SeedKeywordAnalysis.id == analysis_id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    if analysis.status not in ["pending"]:
        raise HTTPException(status_code=400, detail="Analysis cannot be started")
    
    # 在后台运行分析任务
    background_tasks.add_task(run_analysis, analysis.seed_keyword, analysis_id)
    
    return analysis

@router.get("/analysis/{analysis_id}", response_model=AnalysisDetail)
async def get_analysis_result(analysis_id: int, db: Session = Depends(get_db)):
    """获取分析结果"""
    result = get_analysis(db, analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return result

@router.get("/competitors/{analysis_id}", response_model=List[Competitor])
async def get_competitors_endpoint(
    analysis_id: int,
    limit: int = 30,
    db: Session = Depends(get_db)
):
    """获取竞争关键词"""
    competitors = get_competitors(db, analysis_id, limit)
    if not competitors:
        raise HTTPException(status_code=404, detail="Competitors not found")
    return competitors

@router.get("/cooccurrence/{analysis_id}", response_model=List[Cooccurrence])
async def get_cooccurrence_endpoint(analysis_id: int, db: Session = Depends(get_db)):
    """获取共现关键词"""
    cooccurrence = get_cooccurrence(db, analysis_id)
    if not cooccurrence:
        raise HTTPException(status_code=404, detail="Cooccurrence data not found")
    return cooccurrence

@router.get("/search-volume/{analysis_id}", response_model=List[SearchVolume])
async def get_search_volume_endpoint(analysis_id: int, db: Session = Depends(get_db)):
    """获取搜索量分析结果"""
    search_volume = get_search_volume(db, analysis_id)
    if not search_volume:
        raise HTTPException(status_code=404, detail="Search volume data not found")
    return search_volume

@router.get("/history", response_model=List[AnalysisBrief])
async def get_analysis_history(
    skip: int = 0,
    limit: int = 10,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取分析历史"""
    analyses = get_analyses(db, skip=skip, limit=limit, keyword=keyword)
    return analyses 

@router.get("/analysis/{analysis_id}/user-profiles", 
    response_model=dict,
    summary="获取用户画像分析结果",
    description="""
    获取指定分析ID的用户画像分析结果，包括：
    - 用户总数
    - 年龄分布
    - 性别比例
    - 教育程度分布
    - 各维度的详细统计数据
    """
)
async def get_user_profiles_endpoint(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """获取用户画像分析结果"""
    result = get_analysis(db, analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    # 提取用户画像数据
    profile_data = {
        "stats": result.get("user_profile_stats"),
        "distribution": result.get("user_profile_distribution")
    }
    
    if not profile_data["stats"]:
        raise HTTPException(status_code=404, detail="User profile data not found")
        
    return profile_data

@router.get("/analysis/{analysis_id}/user-profiles/stats", 
    response_model=UserProfileStats,
    summary="获取用户画像统计数据",
    description="获取用户画像的汇总统计数据，包括总用户数、平均年龄、性别比例等"
)
async def get_user_profile_stats(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """获取用户画像统计数据"""
    result = get_analysis(db, analysis_id)
    if not result or not result.get("user_profile_stats"):
        raise HTTPException(status_code=404, detail="User profile stats not found")
    return result["user_profile_stats"]

@router.get("/analysis/{analysis_id}/user-profiles/distribution", 
    response_model=List[UserProfileDist],
    summary="获取用户画像分布数据",
    description="获取用户画像的详细分布数据，包括年龄、性别、教育程度的分布情况"
)
async def get_user_profile_distribution(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """获取用户画像分布数据"""
    result = get_analysis(db, analysis_id)
    if not result or not result.get("user_profile_distribution"):
        raise HTTPException(status_code=404, detail="User profile distribution not found")
    return result["user_profile_distribution"] 

@router.post("/analysis/{analysis_id}/market-insights", 
    response_model=str,
    summary="生成市场洞察",
    description="""
    基于指定分析ID的数据生成市场洞察报告，包括：
    - 目标用户分析
    - 市场竞争分析
    - 用户需求洞察
    - 营销策略建议
    - 发展建议
    """
)
async def generate_market_insights(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """生成市场洞察报告"""
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
            
        # 检查是否已有市场洞察
        existing_insight = db.query(models.MarketInsight).filter(
            models.MarketInsight.seed_analysis_id == analysis_id
        ).first()
        
        if existing_insight:
            return existing_insight.content
            
        # 生成新的市场洞察
        insights = await gpt_service.analyze_market_insights(analysis_id, db)
        
        if insights.startswith("市场洞察生成失败"):
            raise HTTPException(
                status_code=500,
                detail=insights
            )
            
        return insights
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成市场洞察失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"生成市场洞察失败: {str(e)}"
        )

@router.get("/analysis/{analysis_id}/market-insights",
    response_model=str,
    summary="获取市场洞察",
    description="获取指定分析ID的市场洞察报告"
)
async def get_market_insights(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """获取市场洞察报告"""
    try:
        insight = db.query(models.MarketInsight).filter(
            models.MarketInsight.seed_analysis_id == analysis_id
        ).first()
        
        if not insight:
            raise HTTPException(
                status_code=404,
                detail=f"Market insights for analysis ID {analysis_id} not found"
            )
            
        return insight.content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取市场洞察失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取市场洞察失败: {str(e)}"
        ) 