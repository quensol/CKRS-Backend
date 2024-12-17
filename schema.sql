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

-- 用户群体画像统计表
CREATE TABLE user_profile_statistics (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    seed_analysis_id BIGINT NOT NULL COMMENT '关联的种子关键词分析ID',
    total_users BIGINT NOT NULL COMMENT '总用户数',
    avg_age DECIMAL(4,2) NOT NULL COMMENT '平均年龄段',
    male_ratio DECIMAL(5,2) NOT NULL COMMENT '男性比例(%)',
    female_ratio DECIMAL(5,2) NOT NULL COMMENT '女性比例(%)',
    avg_education DECIMAL(4,2) NOT NULL COMMENT '平均教育水平',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seed_analysis_id) REFERENCES seed_keyword_analysis(id),
    INDEX idx_seed_analysis_id (seed_analysis_id)
) COMMENT='用户群体画像统计表';

-- 用户画像分布详情表
CREATE TABLE user_profile_distribution (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    seed_analysis_id BIGINT NOT NULL COMMENT '关联的种子关键词分析ID',
    profile_type ENUM('age', 'gender', 'education') NOT NULL COMMENT '画像类型',
    category_value TINYINT NOT NULL COMMENT '类别值',
    user_count BIGINT NOT NULL COMMENT '用户数量',
    percentage DECIMAL(5,2) NOT NULL COMMENT '占比(%)',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seed_analysis_id) REFERENCES seed_keyword_analysis(id),
    INDEX idx_seed_analysis_id (seed_analysis_id),
    INDEX idx_profile_type (profile_type),
    CONSTRAINT chk_category_value CHECK (
        (profile_type = 'age' AND category_value BETWEEN 0 AND 6) OR
        (profile_type = 'gender' AND category_value BETWEEN 0 AND 2) OR
        (profile_type = 'education' AND category_value BETWEEN 0 AND 6)
    )
) COMMENT='用户画像分布详情表';

-- 添加表注释
ALTER TABLE user_profile_distribution 
ADD CONSTRAINT comment_category_values 
CHECK (1=1) /* 
    年龄(age)说明:
    0: 未知年龄
    1: 0-18岁
    2: 19-23岁
    3: 24-30岁
    4: 31-40岁
    5: 41-50岁
    6: 51-999岁

    性别(gender)说明:
    0: 未知
    1: 男性
    2: 女性

    教育程度(education)说明:
    0: 未知学历
    1: 博士
    2: 硕士
    3: 大学生
    4: 高中
    5: 初中
    6: 小学
*/; 

-- 经过GPT过滤的搜索量分析结果表
CREATE TABLE filtered_search_volume_analysis (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    seed_analysis_id BIGINT NOT NULL COMMENT '关联的种子关键词分析ID',
    original_analysis_id BIGINT NOT NULL COMMENT '原始分析记录ID',
    mediator_keyword VARCHAR(100) NOT NULL COMMENT '中介关键词',
    category ENUM('brand', 'attribute', 'function', 'scenario', 'demand', 'other') 
    NOT NULL COMMENT '词语类别(品牌词/属性词/功能词/场景词/需求词/其他词)',
    cooccurrence_volume BIGINT NOT NULL COMMENT '共现搜索量',
    mediator_total_volume BIGINT NOT NULL COMMENT '中介词总搜索量',
    cooccurrence_ratio DECIMAL(10,4) NOT NULL COMMENT '共现比例(%)',
    weight DECIMAL(10,4) NOT NULL COMMENT '权重',
    gpt_confidence DECIMAL(5,2) NOT NULL COMMENT 'GPT分类置信度',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seed_analysis_id) REFERENCES seed_keyword_analysis(id),
    FOREIGN KEY (original_analysis_id) REFERENCES search_volume_analysis(id),
    INDEX idx_seed_analysis_id (seed_analysis_id),
    INDEX idx_category (category),
    INDEX idx_weight (weight)
) COMMENT='经过GPT过滤的搜索量分析结果表';

-- 搜索词分类映射表
CREATE TABLE search_keyword_category_mapping (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    filtered_analysis_id BIGINT NOT NULL COMMENT '关联的过滤后分析ID',
    keyword VARCHAR(100) NOT NULL COMMENT '关键词',
    main_category ENUM('brand', 'attribute', 'function', 'scenario', 'demand', 'other') 
    NOT NULL COMMENT '主要类别',
    sub_category VARCHAR(50) NULL COMMENT '子类别',
    category_description TEXT NULL COMMENT '分类依据说明',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (filtered_analysis_id) REFERENCES filtered_search_volume_analysis(id),
    INDEX idx_keyword (keyword),
    INDEX idx_main_category (main_category)
) COMMENT='搜索词分类映射表';

-- 经过GPT过滤的竞争关键词表
CREATE TABLE filtered_competitor_keywords (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    seed_analysis_id BIGINT NOT NULL COMMENT '关联的种子关键词分析ID',
    original_competitor_id BIGINT NOT NULL COMMENT '原始竞争词记录ID',
    competitor_keyword VARCHAR(100) NOT NULL COMMENT '竞争性关键词',
    competition_type ENUM('direct', 'substitute', 'related', 'scenario', 'other') 
    NOT NULL COMMENT '竞争类型(直接竞品/替代品/相关品/竞争场景/其他)',
    cooccurrence_volume BIGINT NOT NULL COMMENT '共现搜索量',
    base_competition_score DECIMAL(10,4) NOT NULL COMMENT '基础竞争度',
    weighted_competition_score DECIMAL(10,4) NOT NULL COMMENT '加权竞争度',
    gpt_confidence DECIMAL(5,2) NOT NULL COMMENT 'GPT分类置信度',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seed_analysis_id) REFERENCES seed_keyword_analysis(id),
    FOREIGN KEY (original_competitor_id) REFERENCES competitor_keywords(id),
    INDEX idx_seed_analysis_id (seed_analysis_id),
    INDEX idx_competition_type (competition_type),
    INDEX idx_weighted_score (weighted_competition_score)
) COMMENT='经过GPT过滤的竞争关键词表';

-- 竞争词分类映射表
CREATE TABLE competitor_category_mapping (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    filtered_competitor_id BIGINT NOT NULL COMMENT '关联的过滤后竞争词ID',
    keyword VARCHAR(100) NOT NULL COMMENT '关键词',
    main_category ENUM('direct', 'substitute', 'related', 'scenario', 'other') 
    NOT NULL COMMENT '主要竞争类别',
    sub_category VARCHAR(50) NULL COMMENT '子类别',
    category_description TEXT NULL COMMENT '分类依据说明',
    competition_strength DECIMAL(5,2) NOT NULL COMMENT '竞争强度评分',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (filtered_competitor_id) REFERENCES filtered_competitor_keywords(id),
    INDEX idx_keyword (keyword),
    INDEX idx_main_category (main_category)
) COMMENT='竞争词分类映射表';

-- 添加表注释
ALTER TABLE filtered_search_volume_analysis
ADD CONSTRAINT comment_search_categories 
CHECK (1=1) /* 
    搜索词分类说明:
    brand: 品牌词 - 各类品牌名称
    attribute: 属性词 - 描述产品特征的词语
    function: 功能词 - 描述产品功能的词语
    scenario: 场景词 - 使用场景相关词语
    demand: 需求词 - 表达用户需求的词语
    other: 其他词 - 其他有价值但不属于上述类别的词语
*/;

ALTER TABLE filtered_competitor_keywords
ADD CONSTRAINT comment_competitor_categories 
CHECK (1=1) /* 
    竞争词分类说明:
    direct: 直接竞品 - 直接竞争的同类产品
    substitute: 替代品 - 可能替代的其他产品
    related: 相关品 - 相关但不直接竞争的产品
    scenario: 竞争场景 - 体现竞争关系的使用场景
    other: 其他 - 其他有价值的竞争关系词
*/; 

-- 市场洞察结果表
CREATE TABLE market_insights (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    seed_analysis_id BIGINT NOT NULL COMMENT '关联的种子关键词分析ID',
    content TEXT NOT NULL COMMENT '市场洞察内容',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 添加外键约束
    FOREIGN KEY (seed_analysis_id) REFERENCES seed_keyword_analysis(id),
    
    -- 添加索引
    INDEX idx_seed_analysis_id (seed_analysis_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='市场洞察结果表'; 

-- 用户表
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(100) NOT NULL UNIQUE COMMENT '邮箱(账户)',
    password VARCHAR(100) NOT NULL COMMENT '密码(加密存储)',
    phone VARCHAR(20) NOT NULL COMMENT '手机号码',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL COMMENT '最后登录时间',
    INDEX idx_email (email),
    INDEX idx_phone (phone)
) COMMENT='用户表';

-- 修改种子关键词分析记录表,添加用户ID外键
ALTER TABLE seed_keyword_analysis 
ADD COLUMN user_id BIGINT NULL COMMENT '创建用户ID' AFTER id,
ADD FOREIGN KEY (user_id) REFERENCES users(id); 