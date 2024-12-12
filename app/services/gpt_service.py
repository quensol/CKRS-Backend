from openai import AsyncOpenAI
from typing import List, Dict, Any
import json
from app.core.config import settings
import numpy as np
import logging
from app.schemas.filtered_keywords import SearchKeywordCategory, CompetitorKeywordCategory

logger = logging.getLogger(__name__)

class GPTService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        
        # 定义类别映射
        self.category_mapping = {
            'product': 'other',  # 将product映射到other类别
            'brand': 'brand',
            'attribute': 'attribute',
            'function': 'function',
            'scenario': 'scenario',
            'demand': 'demand',
            'other': 'other'
        }
        
    def _validate_category(self, category: str) -> str:
        """
        验证并映射类别
        """
        # 如果类别已经是有效的枚举值，直接返回
        if category in SearchKeywordCategory.__members__:
            return category
            
        # 否则尝试映射
        mapped_category = self.category_mapping.get(category.lower(), 'other')
        logger.warning(f"Category '{category}' mapped to '{mapped_category}'")
        return mapped_category
        
    async def analyze_keywords(self, seed_keyword: str, keywords: List[str], weights: List[float]) -> Dict[str, List[Dict[str, Any]]]:
        """
        使用GPT分析和分类关键词
        """
        # 归一化权重到0-1区间
        normalized_weights = self._normalize_weights(weights)
        
        # 构建关键词和权重的列表
        keyword_list = [
            f"{kw} (weight: {weight:.2f})"
            for kw, weight in zip(keywords, normalized_weights)
        ]
        
        # 构建通用的prompt
        prompt = f"""作为搜索意图分析专家，请仔细分析以下与"{seed_keyword}"相关的共现词列表。

分析要求：
1. 关键词筛选：
   首先判断词语是否与"{seed_keyword}"主题相关：
   - 相关词：与产品、品牌、功能、场景、用户需求等直接相关的词语
   - 无关词：通用词、无意义词、噪声词（如："的"、"了"、"什么"、"最佳"、"推荐"等）
   注意：只对相关词进行分类，无关词直接剔除不返回

2. 品牌与产品识别重点：
   - 识别所有相关品牌名称（包括各种写法变体）
   - 识别产品/服务名称及其变体
   - 识别品牌旗下产品线或服务系列
   - 识别市场新兴品牌或产品

3. 相关词分类（只对相关词进行分类，只能使用以下6个类别之一）：
   - brand: 品牌词
     * 各类品牌名称（官方名称、简称、别名）
     * 品牌系列名称
     * 产品线名称
     * 服务提供商名称

   - attribute: 属性词
     * 产品/服务特征
     * 规格参数
     * 质量特点
     * 区分性特征

   - function: 功能词
     * 核心功能
     * 实现效果
     * 技术特点
     * 服务内容

   - scenario: 场景词
     * 使用场景
     * 适用环境
     * 目标人群
     * 应用情境

   - demand: 需求词
     * 用户痛点
     * 目标诉求
     * 期望价值
     * 解决方案

   - other: 其他相关词
     * 重要的行业术语
     * 核心相关概念
     * 关键评价指标
     * 重要技术标准

注意：必须使用以上6个类别之一，不要使用其他类别名称。

4. 分类原则：
   - 只对相关词进行分类，无关词直接剔除
   - 每个相关词归入最适合的单一类别
   - 优先识别品牌和产品名称
   - 基于词语在当前领域的主要含义分类
   - 提供具体的分类依据
   - 给出分类置信度(0-100)

共现词列表（包含归一化权重）：
{json.dumps(keyword_list, ensure_ascii=False, indent=2)}

请以以下JSON格式返回结果（只返回相关词的分类结果）：
{{
    "classifications": [
        {{
            "keyword": "词语",
            "category": "类别",
            "confidence": 置信度,
            "weight": 权重,
            "reason": "分类依据"
        }},
        ...
    ]
}}

只返回JSON，不要其他说明。"""

        try:
            # 记录完整的prompt（使用encode和decode处理编码问题）
            logger.info(prompt.encode('utf-8').decode('utf-8'))
            
            # 调用GPT API
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": """你是一个专业的搜索意图分析专家，精通跨领域的关键词分析和分类。
你具有：
1. 广泛的品牌知识，能识别各行业的品牌、产品和服务名称
2. 深入的多领域理解，熟悉不同行业的专业术语和概念
3. 精准的分类能力，能根据上下文准确判断词语类别
4. 严谨的分析态度，提供详实的分类依据
5. 灵活的判断力，能根据不同领域调整分类标准"""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # 验证和修正类别
            for item in result.get('classifications', []):
                if 'category' in item:
                    item['category'] = self._validate_category(item['category'])
            
            # 记录GPT的响应（使用encode和decode处理编码问题）
            logger.info(json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8').decode('utf-8'))
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"GPT返回的结果解析失败: {str(e)}")
            raise ValueError(f"GPT返回的结果不是有效的JSON格式: {str(e)}")
        except Exception as e:
            logger.error(f"处理过程中发生错误: {str(e)}")
            raise
            
    def _normalize_weights(self, weights: List[float]) -> List[float]:
        """
        将权重归一化到0-1区间
        """
        if not weights:
            return []
        weights_array = np.array(weights)
        min_weight = weights_array.min()
        max_weight = weights_array.max()
        if max_weight == min_weight:
            return [1.0] * len(weights)
        normalized = (weights_array - min_weight) / (max_weight - min_weight)
        return normalized.tolist() 