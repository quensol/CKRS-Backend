from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AnalysisBase(BaseModel):
    seed_keyword: str

class AnalysisCreate(AnalysisBase):
    pass

class AnalysisBrief(AnalysisBase):
    id: int
    status: str
    error_message: Optional[str] = None
    total_search_volume: int
    seed_search_volume: int
    seed_search_ratio: float
    created_at: datetime

    class Config:
        from_attributes = True

class Cooccurrence(BaseModel):
    keyword: str
    cooccurrence_count: int

    class Config:
        from_attributes = True

class SearchVolume(BaseModel):
    mediator_keyword: str
    cooccurrence_volume: int
    mediator_total_volume: int
    cooccurrence_ratio: float
    weight: float

    class Config:
        from_attributes = True

class Competitor(BaseModel):
    competitor_keyword: str
    mediator_keywords: str
    cooccurrence_volume: int
    base_competition_score: float
    weighted_competition_score: float

    class Config:
        from_attributes = True

class AnalysisDetail(AnalysisBrief):
    cooccurrence_keywords: List[Cooccurrence]
    search_volumes: List[SearchVolume]
    competitors: List[Competitor]

    class Config:
        from_attributes = True 