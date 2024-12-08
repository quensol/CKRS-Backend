from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.keyword import (
    AnalysisBrief,
    Cooccurrence,
    SearchVolume,
    Competitor,
    AnalysisDetail
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

router = APIRouter()

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