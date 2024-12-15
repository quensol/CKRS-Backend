from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class SearchKeywordCategory(str, Enum):
    brand = "brand"
    attribute = "attribute"
    function = "function"
    scenario = "scenario"
    demand = "demand"
    other = "other"

class CompetitorKeywordCategory(str, Enum):
    direct = "direct"
    substitute = "substitute"
    related = "related"
    scenario = "scenario"
    other = "other"

class FilteredSearchVolumeCreate(BaseModel):
    mediator_keyword: str
    category: SearchKeywordCategory
    gpt_confidence: float = Field(..., ge=0, le=100)
    sub_category: Optional[str] = None
    category_description: Optional[str] = None

class FilteredCompetitorCreate(BaseModel):
    competitor_keyword: str
    competition_type: CompetitorKeywordCategory
    gpt_confidence: float = Field(..., ge=0, le=100)
    sub_category: Optional[str] = None
    category_description: Optional[str] = None
    competition_strength: Optional[float] = Field(None, ge=0, le=100)

class FilteredSearchVolumeResponse(BaseModel):
    id: int
    mediator_keyword: str
    category: SearchKeywordCategory
    cooccurrence_volume: int
    weight: float
    gpt_confidence: float
    created_at: datetime

class FilteredCompetitorResponse(BaseModel):
    id: int
    competitor_keyword: str
    competition_type: CompetitorKeywordCategory
    cooccurrence_volume: int
    weighted_competition_score: float
    gpt_confidence: float
    created_at: datetime 