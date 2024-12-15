from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.keyword import SeedKeywordAnalysis, SearchVolumeAnalysis, CompetitorKeyword
from app.models.filtered_keywords import (
    FilteredSearchVolumeAnalysis,
    FilteredCompetitorKeywords
)
from app.services.gpt_service import GPTService
from app.core.logger import logger
from sqlalchemy import desc
import pandas as pd

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
                
            # 获取原始搜索量分析数据，按权重排序取前100个
            search_volumes = self.db.query(SearchVolumeAnalysis).filter(
                SearchVolumeAnalysis.seed_analysis_id == analysis_id
            ).order_by(desc(SearchVolumeAnalysis.weight)).limit(100).all()
            
            if not search_volumes:
                logger.warning(f"No search volume data found for analysis {analysis_id}")
                return
                
            # 准备GPT分析数据
            keywords = [item.mediator_keyword for item in search_volumes]
            weights = [float(item.weight) for item in search_volumes]
            
            # 调用GPT服务进行分析
            result = await self.gpt_service.analyze_keywords(
                seed_keyword=seed_analysis.seed_keyword,
                keywords=keywords,
                weights=weights
            )
            
            # 保存过滤结果
            for item in result.get('classifications', []):
                try:
                    # 查找原始数据
                    original_volume = next(
                        (sv for sv in search_volumes if sv.mediator_keyword == item['keyword']),
                        None
                    )
                    
                    if not original_volume:
                        logger.warning(f"Original data not found for keyword: {item['keyword']}")
                        continue
                        
                    # 创建过滤结果记录
                    filtered_volume = FilteredSearchVolumeAnalysis(
                        seed_analysis_id=analysis_id,
                        original_analysis_id=original_volume.id,
                        mediator_keyword=item['keyword'],
                        category=item['category'],
                        cooccurrence_volume=original_volume.cooccurrence_volume,
                        mediator_total_volume=original_volume.mediator_total_volume,
                        cooccurrence_ratio=original_volume.cooccurrence_ratio,
                        weight=original_volume.weight,
                        gpt_confidence=item['confidence']
                    )
                    
                    self.db.add(filtered_volume)
                    
                except Exception as e:
                    logger.error(f"Error processing keyword {item.get('keyword')}: {str(e)}")
                    continue
                    
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
            # 获取种子关键词
            seed_analysis = self.db.query(SeedKeywordAnalysis).filter(
                SeedKeywordAnalysis.id == analysis_id
            ).first()
            
            if not seed_analysis:
                raise ValueError(f"Analysis {analysis_id} not found")
                
            # 获取原始竞争关键词数据，按加权竞争度排序取前100个
            competitors = self.db.query(CompetitorKeyword).filter(
                CompetitorKeyword.seed_analysis_id == analysis_id
            ).order_by(desc(CompetitorKeyword.weighted_competition_score)).limit(100).all()
            
            if not competitors:
                logger.warning(f"No competitor data found for analysis {analysis_id}")
                return
                
            # 准备GPT分析数据
            keywords = [item.competitor_keyword for item in competitors]
            weights = [float(item.weighted_competition_score) for item in competitors]
            
            # 调用GPT服务进行分析
            result = await self.gpt_service.analyze_competitors(
                seed_keyword=seed_analysis.seed_keyword,
                competitors=keywords,
                weights=weights
            )
            
            # 保存过滤结果
            for item in result.get('classifications', []):
                try:
                    # 查找原始数据
                    original_competitor = next(
                        (c for c in competitors if c.competitor_keyword == item['keyword']),
                        None
                    )
                    
                    if not original_competitor:
                        logger.warning(f"Original data not found for competitor: {item['keyword']}")
                        continue
                        
                    # 创建过滤结果记录
                    filtered_competitor = FilteredCompetitorKeywords(
                        seed_analysis_id=analysis_id,
                        original_competitor_id=original_competitor.id,
                        competitor_keyword=item['keyword'],
                        competition_type=item['category'],
                        cooccurrence_volume=original_competitor.cooccurrence_volume,
                        base_competition_score=original_competitor.base_competition_score,
                        weighted_competition_score=original_competitor.weighted_competition_score,
                        gpt_confidence=item['confidence']
                    )
                    
                    self.db.add(filtered_competitor)
                    
                except Exception as e:
                    logger.error(f"Error processing competitor {item.get('keyword')}: {str(e)}")
                    continue
                    
            self.db.commit()
            logger.info(f"Analysis {analysis_id} competitors filtering completed")
            
        except Exception as e:
            self.db.rollback()
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