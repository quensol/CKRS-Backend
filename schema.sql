-- 创建数据库
CREATE DATABASE IF NOT EXISTS keyword_analysis DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE keyword_analysis;

-- 种子关键词分析记录表
CREATE TABLE seed_keyword_analysis (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    seed_keyword VARCHAR(100) NOT NULL COMMENT '种子关键词',
    total_search_volume BIGINT NOT NULL COMMENT '总查询量',
    seed_search_volume BIGINT NOT NULL COMMENT '种子关键词搜索量',
    seed_search_ratio DECIMAL(10,4) NOT NULL COMMENT '种子关键词搜索占比(%)',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_seed_keyword (seed_keyword),
    INDEX idx_created_at (created_at)
) COMMENT='种子关键词分析记录表';

-- 共现关键词表
CREATE TABLE cooccurrence_keywords (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    seed_analysis_id BIGINT NOT NULL COMMENT '关联的种子关键词分析ID',
    keyword VARCHAR(100) NOT NULL COMMENT '共现关键词',
    cooccurrence_count INT NOT NULL COMMENT '共现次数',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seed_analysis_id) REFERENCES seed_keyword_analysis(id),
    INDEX idx_seed_analysis_id (seed_analysis_id),
    INDEX idx_keyword (keyword)
) COMMENT='共现关键词表';

-- 搜索量分析结果表
CREATE TABLE search_volume_analysis (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    seed_analysis_id BIGINT NOT NULL COMMENT '关联的种子关键词分析ID',
    mediator_keyword VARCHAR(100) NOT NULL COMMENT '中介关键词',
    cooccurrence_volume BIGINT NOT NULL COMMENT '共现搜索量',
    mediator_total_volume BIGINT NOT NULL COMMENT '中介词总搜索量',
    cooccurrence_ratio DECIMAL(10,4) NOT NULL COMMENT '共现比例(%)',
    weight DECIMAL(10,4) NOT NULL COMMENT '权重',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seed_analysis_id) REFERENCES seed_keyword_analysis(id),
    INDEX idx_seed_analysis_id (seed_analysis_id),
    INDEX idx_mediator_keyword (mediator_keyword),
    INDEX idx_weight (weight)
) COMMENT='搜索量分析结果表';

-- 竞争关键词表
CREATE TABLE competitor_keywords (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    seed_analysis_id BIGINT NOT NULL COMMENT '关联的种子关键词分析ID',
    competitor_keyword VARCHAR(100) NOT NULL COMMENT '竞争性关键词',
    mediator_keywords TEXT NOT NULL COMMENT '关联的中介关键词(逗号分隔)',
    cooccurrence_volume BIGINT NOT NULL COMMENT '共现搜索量',
    base_competition_score DECIMAL(10,4) NOT NULL COMMENT '基础竞争度',
    weighted_competition_score DECIMAL(10,4) NOT NULL COMMENT '加权竞争度',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seed_analysis_id) REFERENCES seed_keyword_analysis(id),
    INDEX idx_seed_analysis_id (seed_analysis_id),
    INDEX idx_competitor_keyword (competitor_keyword),
    INDEX idx_weighted_score (weighted_competition_score)
) COMMENT='竞争关键词表';

-- 修改种子关键词分析记录表，添加状态字段
ALTER TABLE seed_keyword_analysis 
ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending' 
COMMENT '分析状态: pending/processing/completed/failed' AFTER seed_keyword,
ADD COLUMN error_message TEXT NULL COMMENT '错误信息' AFTER status,
ADD INDEX idx_status (status); 