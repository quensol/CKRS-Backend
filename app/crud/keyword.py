from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.keyword import (
    SeedKeywordAnalysis,
    CooccurrenceKeyword,
    SearchVolumeAnalysis,
    CompetitorKeyword
)
from app.schemas.keyword import (
    AnalysisCreate,
    AnalysisBrief
)
from fastapi.encoders import jsonable_encoder

def create_analysis(db: Session, analyzer_result: dict) -> SeedKeywordAnalysis:
    db_analysis = SeedKeywordAnalysis(
        seed_keyword=analyzer_result["seed_keyword"],
        total_search_volume=analyzer_result["total_search_volume"],
        seed_search_volume=analyzer_result["seed_search_volume"],
        seed_search_ratio=analyzer_result["seed_search_ratio"]
    )
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)
    return db_analysis

def get_analysis(db: Session, analysis_id: int) -> Optional[dict]:
    """获取完整的分析结果"""
    # 获取基本分析记录
    analysis = db.query(SeedKeywordAnalysis).filter(
        SeedKeywordAnalysis.id == analysis_id
    ).first()
    
    if not analysis:
        return None
        
    # 获取共现关键词
    cooccurrence = db.query(CooccurrenceKeyword).filter(
        CooccurrenceKeyword.seed_analysis_id == analysis_id
    ).order_by(CooccurrenceKeyword.cooccurrence_count.desc()).all()
    
    # 获取搜索量分析
    search_volumes = db.query(SearchVolumeAnalysis).filter(
        SearchVolumeAnalysis.seed_analysis_id == analysis_id
    ).order_by(SearchVolumeAnalysis.weight.desc()).all()
    
    # 获取竞争关键词
    competitors = db.query(CompetitorKeyword).filter(
        CompetitorKeyword.seed_analysis_id == analysis_id
    ).order_by(CompetitorKeyword.weighted_competition_score.desc()).all()
    
    # 构建完整的返回结果
    result = {
        "id": analysis.id,
        "seed_keyword": analysis.seed_keyword,
        "status": analysis.status,
        "total_search_volume": analysis.total_search_volume,
        "seed_search_volume": analysis.seed_search_volume,
        "seed_search_ratio": float(analysis.seed_search_ratio),
        "created_at": analysis.created_at,
        "cooccurrence_keywords": cooccurrence,
        "search_volumes": search_volumes,
        "competitors": competitors
    }
    
    return result

def get_analyses(
    db: Session, 
    skip: int = 0, 
    limit: int = 10,
    keyword: Optional[str] = None
) -> List[SeedKeywordAnalysis]:
    query = db.query(SeedKeywordAnalysis)
    if keyword:
        query = query.filter(SeedKeywordAnalysis.seed_keyword.contains(keyword))
    return query.offset(skip).limit(limit).all()

def get_competitors(
    db: Session, 
    analysis_id: int,
    limit: int = 30
) -> List[CompetitorKeyword]:
    """同步获取竞争关键词"""
    result = db.query(CompetitorKeyword).filter(
        CompetitorKeyword.seed_analysis_id == analysis_id
    ).order_by(
        CompetitorKeyword.weighted_competition_score.desc()
    ).limit(limit).all()
    return result

def get_cooccurrence(db: Session, analysis_id: int) -> List[CooccurrenceKeyword]:
    """获取共现关键词数据"""
    return db.query(CooccurrenceKeyword).filter(
        CooccurrenceKeyword.seed_analysis_id == analysis_id
    ).order_by(CooccurrenceKeyword.cooccurrence_count.desc()).all()

def get_search_volume(db: Session, analysis_id: int) -> List[SearchVolumeAnalysis]:
    """获取搜索量分析数据"""
    return db.query(SearchVolumeAnalysis).filter(
        SearchVolumeAnalysis.seed_analysis_id == analysis_id
    ).order_by(SearchVolumeAnalysis.weight.desc()).all() 