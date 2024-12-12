from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.sql import func
from app.core.database import Base
from app.schemas.filtered_keywords import SearchKeywordCategory, CompetitorKeywordCategory

class FilteredSearchVolumeAnalysis(Base):
    """过滤后的搜索量分析结果表"""
    __tablename__ = "filtered_search_volume_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    seed_analysis_id = Column(Integer, ForeignKey("seed_keyword_analysis.id"), nullable=False)
    original_analysis_id = Column(Integer, ForeignKey("search_volume_analysis.id"), nullable=False)
    mediator_keyword = Column(String(255), nullable=False)
    category = Column(Enum(SearchKeywordCategory), nullable=False)
    cooccurrence_volume = Column(Integer, nullable=False)
    mediator_total_volume = Column(Integer, nullable=False)
    cooccurrence_ratio = Column(Float, nullable=False)
    weight = Column(Float, nullable=False)
    gpt_confidence = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        {"comment": "过滤后的搜索量分析结果表"}
    )

class SearchKeywordCategoryMapping(Base):
    """搜索词分类映射表"""
    __tablename__ = "search_keyword_category_mapping"
    
    id = Column(Integer, primary_key=True, index=True)
    filtered_analysis_id = Column(Integer, ForeignKey("filtered_search_volume_analysis.id"), nullable=False)
    keyword = Column(String(255), nullable=False)
    main_category = Column(Enum(SearchKeywordCategory), nullable=False)
    sub_category = Column(String(50))
    category_description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        {"comment": "搜索词分类映射表"}
    )

class FilteredCompetitorKeywords(Base):
    """过滤后的竞争关键词表"""
    __tablename__ = "filtered_competitor_keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    seed_analysis_id = Column(Integer, ForeignKey("seed_keyword_analysis.id"), nullable=False)
    original_competitor_id = Column(Integer, ForeignKey("competitor_keyword.id"), nullable=False)
    competitor_keyword = Column(String(255), nullable=False)
    competition_type = Column(Enum(CompetitorKeywordCategory), nullable=False)
    cooccurrence_volume = Column(Integer, nullable=False)
    weighted_competition_score = Column(Float, nullable=False)
    gpt_confidence = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        {"comment": "过滤后的竞争关键词表"}
    )

class CompetitorCategoryMapping(Base):
    """竞争词分类映射表"""
    __tablename__ = "competitor_category_mapping"
    
    id = Column(Integer, primary_key=True, index=True)
    filtered_competitor_id = Column(Integer, ForeignKey("filtered_competitor_keywords.id"), nullable=False)
    keyword = Column(String(255), nullable=False)
    competition_type = Column(Enum(CompetitorKeywordCategory), nullable=False)
    competition_strength = Column(Float)
    category_description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        {"comment": "竞争词分类映射表"}
    ) 