from sqlalchemy.orm import Session
from app.models.keyword import (
    SeedKeywordAnalysis,
    SearchVolumeAnalysis,
    CompetitorKeyword
)
from app.models.filtered_keywords import (
    FilteredSearchVolumeAnalysis,
    SearchKeywordCategoryMapping,
    FilteredCompetitorKeywords,
    CompetitorCategoryMapping
)
from app.services.gpt_service import GPTService
from typing import List, Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

class GPTFilterService:
    def __init__(self, db: Session):
        self.db = db
        self.gpt_service = GPTService()
        
    async def filter_search_volume(self, analysis_id: int):
        """
        使用GPT过滤和分类搜索量分析结果
        """
        try:
            # 获取种子关键词
            seed_analysis = self.db.query(SeedKeywordAnalysis).filter(
                SeedKeywordAnalysis.id == analysis_id
            ).first()
            
            if not seed_analysis:
                raise ValueError(f"Analysis {analysis_id} not found")
            
            # 获取原始搜索量分析数据（按权重排序，取前100个）
            search_volumes = self.db.query(SearchVolumeAnalysis).filter(
                SearchVolumeAnalysis.seed_analysis_id == analysis_id
            ).order_by(SearchVolumeAnalysis.weight.desc()).limit(100).all()
            
            if not search_volumes:
                logger.warning(f"No search volumes found for analysis {analysis_id}")
                return
            
            # 提取关键词和权重
            keywords = [sv.mediator_keyword for sv in search_volumes]
            weights = [float(sv.weight) for sv in search_volumes]
            
            # 调用GPT服务进行分析
            result = await self.gpt_service.analyze_keywords(
                seed_analysis.seed_keyword,
                keywords,
                weights
            )
            
            # 保存过滤结果
            for item in result["classifications"]:
                # 创建过滤后的搜索量分析记录
                original_volume = next(
                    sv for sv in search_volumes 
                    if sv.mediator_keyword == item["keyword"]
                )
                
                filtered_volume = FilteredSearchVolumeAnalysis(
                    seed_analysis_id=analysis_id,
                    original_analysis_id=original_volume.id,
                    mediator_keyword=item["keyword"],
                    category=item["category"],
                    cooccurrence_volume=original_volume.cooccurrence_volume,
                    mediator_total_volume=original_volume.mediator_total_volume,
                    cooccurrence_ratio=original_volume.cooccurrence_ratio,
                    weight=original_volume.weight,
                    gpt_confidence=item["confidence"]
                )
                self.db.add(filtered_volume)
                self.db.flush()  # 获取ID
                
                # 创建分类映射记录
                category_mapping = SearchKeywordCategoryMapping(
                    filtered_analysis_id=filtered_volume.id,
                    keyword=item["keyword"],
                    main_category=item["category"],
                    category_description=item["reason"]
                )
                self.db.add(category_mapping)
            
            self.db.commit()
            logger.info(f"Analysis {analysis_id} search volume filtering completed")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error filtering search volume for analysis {analysis_id}: {str(e)}")
            raise
            
    async def filter_competitors(self, analysis_id: int):
        """
        使用GPT过滤和分类竞争关键词
        """
        try:
            # 获取原始竞争关键词数据
            competitors = self.db.query(CompetitorKeyword).filter(
                CompetitorKeyword.seed_analysis_id == analysis_id
            ).all()
            
            # TODO: 实现GPT过滤和分类逻辑
            
            # 保存过滤结果
            
            logger.info(f"Analysis {analysis_id} competitors filtering completed")
            
        except Exception as e:
            logger.error(f"Error filtering competitors for analysis {analysis_id}: {str(e)}")
            raise
            
    def get_filtered_search_volume(self, analysis_id: int) -> List[Dict[str, Any]]:
        """
        获取已过滤的搜索量分析结果
        """
        results = self.db.query(FilteredSearchVolumeAnalysis).filter(
            FilteredSearchVolumeAnalysis.seed_analysis_id == analysis_id
        ).order_by(FilteredSearchVolumeAnalysis.weight.desc()).all()
        
        return [
            {
                "id": result.id,
                "mediator_keyword": result.mediator_keyword,
                "category": result.category,
                "cooccurrence_volume": result.cooccurrence_volume,
                "weight": float(result.weight),
                "gpt_confidence": float(result.gpt_confidence),
                "created_at": result.created_at
            }
            for result in results
        ]
        
    def get_filtered_competitors(self, analysis_id: int) -> List[Dict[str, Any]]:
        """
        获取已过滤的竞争关键词
        """
        # TODO: 实现获取过滤后的竞争关键词
        pass 