from sqlalchemy import Column, Integer, String, DECIMAL, TIMESTAMP, BigInteger, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class SeedKeywordAnalysis(Base):
    __tablename__ = "seed_keyword_analysis"

    id = Column(BigInteger, primary_key=True, index=True)
    seed_keyword = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    total_search_volume = Column(BigInteger, nullable=False)
    seed_search_volume = Column(BigInteger, nullable=False)
    seed_search_ratio = Column(DECIMAL(10,4), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, default=func.current_timestamp())

    # 添加关系
    cooccurrence_keywords = relationship("CooccurrenceKeyword", back_populates="analysis")
    search_volumes = relationship("SearchVolumeAnalysis", back_populates="analysis")
    competitors = relationship("CompetitorKeyword", back_populates="analysis")
    user_profile_stats = relationship("UserProfileStatistics", back_populates="analysis")
    user_profile_dist = relationship("UserProfileDistribution", back_populates="analysis")

class CooccurrenceKeyword(Base):
    __tablename__ = "cooccurrence_keywords"

    id = Column(BigInteger, primary_key=True, index=True)
    seed_analysis_id = Column(BigInteger, ForeignKey("seed_keyword_analysis.id"))
    keyword = Column(String(100), nullable=False, index=True)
    cooccurrence_count = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 添加关系
    analysis = relationship("SeedKeywordAnalysis", back_populates="cooccurrence_keywords")

class SearchVolumeAnalysis(Base):
    __tablename__ = "search_volume_analysis"

    id = Column(BigInteger, primary_key=True, index=True)
    seed_analysis_id = Column(BigInteger, ForeignKey("seed_keyword_analysis.id"))
    mediator_keyword = Column(String(100), nullable=False, index=True)
    cooccurrence_volume = Column(BigInteger, nullable=False)
    mediator_total_volume = Column(BigInteger, nullable=False)
    cooccurrence_ratio = Column(DECIMAL(10,4), nullable=False)
    weight = Column(DECIMAL(10,4), nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 添加关系
    analysis = relationship("SeedKeywordAnalysis", back_populates="search_volumes")

class CompetitorKeyword(Base):
    __tablename__ = "competitor_keywords"

    id = Column(BigInteger, primary_key=True, index=True)
    seed_analysis_id = Column(BigInteger, ForeignKey("seed_keyword_analysis.id"))
    competitor_keyword = Column(String(100), nullable=False, index=True)
    mediator_keywords = Column(Text, nullable=False)
    cooccurrence_volume = Column(BigInteger, nullable=False)
    base_competition_score = Column(DECIMAL(10,4), nullable=False)
    weighted_competition_score = Column(DECIMAL(10,4), nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 添加关系
    analysis = relationship("SeedKeywordAnalysis", back_populates="competitors") 

class UserProfileStatistics(Base):
    __tablename__ = "user_profile_statistics"
    
    id = Column(BigInteger, primary_key=True, index=True)
    seed_analysis_id = Column(BigInteger, ForeignKey("seed_keyword_analysis.id"))
    total_users = Column(BigInteger, nullable=False)
    avg_age = Column(DECIMAL(4,2), nullable=False)
    male_ratio = Column(DECIMAL(5,2), nullable=False)
    female_ratio = Column(DECIMAL(5,2), nullable=False)
    avg_education = Column(DECIMAL(4,2), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # 添加关系
    analysis = relationship("SeedKeywordAnalysis", back_populates="user_profile_stats")

class UserProfileDistribution(Base):
    __tablename__ = "user_profile_distribution"
    
    id = Column(BigInteger, primary_key=True, index=True)
    seed_analysis_id = Column(BigInteger, ForeignKey("seed_keyword_analysis.id"))
    profile_type = Column(String(10), nullable=False)
    category_value = Column(Integer, nullable=False)
    user_count = Column(BigInteger, nullable=False)
    percentage = Column(DECIMAL(5,2), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # 添加关系
    analysis = relationship("SeedKeywordAnalysis", back_populates="user_profile_dist") 