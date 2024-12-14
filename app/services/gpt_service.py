from openai import AsyncOpenAI
from typing import List, Dict, Any
import json
from app.core.config import settings
import numpy as np
import logging
from app.schemas.filtered_keywords import SearchKeywordCategory, CompetitorKeywordCategory
from sqlalchemy.orm import Session
from app import models
from app.core.logger import logger

logger = logging.getLogger(__name__)

class GPTService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        
        # 定义搜索关键词类别映射
        self.search_category_mapping = {
            'product': 'other',
            'brand': 'brand',
            'attribute': 'attribute',
            'function': 'function',
            'scenario': 'scenario',
            'demand': 'demand',
            'other': 'other'
        }
        
        # 定义竞争关键词类别映射
        self.competitor_category_mapping = {
            'direct': 'direct',
            'substitute': 'substitute',
            'related': 'related',
            'scenario': 'scenario',
            'other': 'other'
        }
        
    def _validate_search_category(self, category: str) -> str:
        """
        验证并映射搜索关键词类别
        """
        if category in SearchKeywordCategory.__members__:
            return category
            
        mapped_category = self.search_category_mapping.get(category.lower(), 'other')
        logger.warning(f"Search category '{category}' mapped to '{mapped_category}'")
        return mapped_category
        
    def _validate_competitor_category(self, category: str) -> str:
        """
        验证并映射竞争关键词类别
        """
        if category in CompetitorKeywordCategory.__members__:
            return category
            
        mapped_category = self.competitor_category_mapping.get(category.lower(), 'other')
        logger.warning(f"Competitor category '{category}' mapped to '{mapped_category}'")
        return mapped_category
        
    async def analyze_keywords(self, seed_keyword: str, keywords: List[str], weights: List[float]) -> Dict[str, List[Dict[str, Any]]]:
        """
        使用GPT分析和分类关键词
        """
        try:
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

            # 记录完整的prompt
            logger.info(f"Sending prompt to GPT:\n{prompt}")
            
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
            
            # 记录原始响应
            logger.info(f"Raw GPT response:\n{response}")
            
            # 获取响应内容并清理
            content = response.choices[0].message.content
            if not content:
                raise ValueError("GPT returned empty response")
                
            # 清理可能的Markdown代码块标记
            content = content.strip()
            if content.startswith('```'):
                # 移除开头的```json或```
                content = content.split('\n', 1)[1]
            if content.endswith('```'):
                # 移除结尾的```
                content = content.rsplit('\n', 1)[0]
                
            logger.info(f"Cleaned GPT response content:\n{content}")
            
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse cleaned GPT response: {content}")
                raise ValueError(f"Invalid JSON response from GPT: {str(e)}")
            
            # 验证响应格式
            if not isinstance(result, dict) or 'classifications' not in result:
                raise ValueError(f"Unexpected response format: {result}")
            
            # 验证和修正类别
            for item in result.get('classifications', []):
                if 'category' not in item:
                    logger.warning(f"Missing category in item: {item}")
                    continue
                item['category'] = self._validate_search_category(item['category'])
            
            # 记录处理后的结果
            logger.info(f"Processed result:\n{json.dumps(result, ensure_ascii=False, indent=2)}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise ValueError(f"GPT返回的结果不是有效的JSON格式: {str(e)}")
        except Exception as e:
            logger.error(f"Error in analyze_keywords: {str(e)}")
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
        
    async def analyze_competitors(self, seed_keyword: str, competitors: List[str], weights: List[float]) -> Dict[str, List[Dict[str, Any]]]:
        """
        分析竞争关键词
        """
        try:
            # 归一化权重到0-1区间，保留2位小数
            normalized_weights = [round(w, 2) for w in self._normalize_weights(weights)]
            
            # 构建关键词和权重的列表
            competitor_list = [
                f"{kw} (weight: {weight})"
                for kw, weight in zip(competitors, normalized_weights)
            ]
            
            # 构建优化后的prompt
            prompt = f"""作为竞争分析专家，请仔细分析以下与"{seed_keyword}"相关的竞争关键词列表。

分析要求：
1. 关键词筛选：
   首先判断词语是否体现竞争关系：
   - 相关词：与竞争态势、市场竞争、用户选择等直接相关的词语
   - 无关词：通用词、无意义词、噪声词（如："的"、"了"、"什么"、"最佳"、"推荐"等）
   注意：只对相关词进行分类，无关词直接剔除不返回

2. 竞争关系识别重点：
   - 识别直接竞争的品牌和产品
   - 识别潜在的替代品和替代方案
   - 识别重要的竞争场景和场合
   - 识别市场竞争的关键因素

3. 竞争词分类（只对相关词进行分类，只能使用以下5个类别之一）：
   - direct: 直接竞品
     * 直接竞争的同类产品
     * 主要竞争品牌
     * 核心竞品系列

   - substitute: 替代品
     * 可能替代的其他产品
     * 替代解决方案
     * 潜在替代品类

   - related: 相关品
     * 相关但不直接竞争的产品
     * 互补产品
     * 相关品类

   - scenario: 竞争场景
     * 体现竞争关系的使用场景
     * 竞争发生的关键场合
     * 用户选择的决策场景

   - other: 其他竞争词
     * 重要的竞争关系词
     * 关键竞争因素
     * 市场竞争态势

注意：必须使用以上5个类别之一，不要使用其他类别名称。

4. 分类原则：
   - 只对体现竞争关系的词语进行分类，无关词直接剔除
   - 每个相关词归入最适合的单一类别
   - 优先识别直接竞品和替代品
   - 基于词语在竞争分析中的主要作用分类
   - 提供具体的竞争关系说明
   - 给出分类置信度(0-100)

竞争词列表（包含归一化权重）：
{json.dumps(competitor_list, ensure_ascii=False, indent=2)}

请以以下JSON格式返回结果（只返回相关词的分类结果）：
{{
    "classifications": [
        {{
            "keyword": "词语",
            "category": "类别",
            "confidence": 置信度,
            "weight": 权重,
            "reason": "竞争关系说明"
        }},
        ...
    ]
}}

只返回JSON，不要其他说明。"""

            # 记录完整的prompt
            logger.info(f"Sending prompt to GPT:\n{prompt}")
            
            # 调用GPT API
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": """你是一个专业的竞争分析专家，精通市场竞争分析。
你具有：
1. 敏锐的竞争洞察力，能准确识别竞争关系
2. 深入的市场理解，熟悉各类竞争形态
3. 精准的分类能力，能准确判断竞争要素
4. 系统的分析思维，提供详实的竞争分析
5. 战略性的判断力，能识别关键竞争因素"""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # 记录原始响应
            logger.info(f"Raw GPT response:\n{response}")
            
            # 获取响应内容并清理
            content = response.choices[0].message.content
            if not content:
                raise ValueError("GPT returned empty response")
                
            # 清理可能的Markdown代码块标记
            content = content.strip()
            if content.startswith('```'):
                # 移除开头的```json或```
                content = content.split('\n', 1)[1]
            if content.endswith('```'):
                # 移除结尾的```
                content = content.rsplit('\n', 1)[0]
                
            logger.info(f"Cleaned GPT response content:\n{content}")
            
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse cleaned GPT response: {content}")
                raise ValueError(f"Invalid JSON response from GPT: {str(e)}")
            
            # 验证响应格式
            if not isinstance(result, dict) or 'classifications' not in result:
                raise ValueError(f"Unexpected response format: {result}")
            
            # 验证和修正类别
            for item in result.get('classifications', []):
                if 'category' not in item:
                    logger.warning(f"Missing category in item: {item}")
                    continue
                item['category'] = self._validate_competitor_category(item['category'])
            
            # 记录处理后的结果
            logger.info(f"Processed result:\n{json.dumps(result, ensure_ascii=False, indent=2)}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise ValueError(f"GPT返回的结果不是有效的JSON格式: {str(e)}")
        except Exception as e:
            logger.error(f"Error in analyze_competitors: {str(e)}")
            raise
        
    async def analyze_market_insights(self, analysis_id: int, db: Session) -> str:
        """使用GPT分析市场洞察"""
        try:
            logger.info(f"准备分析ID {analysis_id} 的市场洞察数据...")
            
            # 1. 获取基础分析信息
            analysis = db.query(models.SeedKeywordAnalysis).filter(
                models.SeedKeywordAnalysis.id == analysis_id
            ).first()
            
            if not analysis:
                raise ValueError(f"未找到ID为 {analysis_id} 的分析记录")
            
            keyword = analysis.seed_keyword
            
            # 2. 获取用户画像数据
            profile_stats = db.query(models.UserProfileStatistics).filter(
                models.UserProfileStatistics.seed_analysis_id == analysis_id
            ).first()
            
            profile_dist = db.query(models.UserProfileDistribution).filter(
                models.UserProfileDistribution.seed_analysis_id == analysis_id
            ).all()
            
            # 整理用户画像分布数据
            demographics = {}
            if profile_stats:
                demographics = {
                    'total_users': profile_stats.total_users,
                    'avg_age': float(profile_stats.avg_age),
                    'male_ratio': float(profile_stats.male_ratio),
                    'female_ratio': float(profile_stats.female_ratio),
                    'avg_education': float(profile_stats.avg_education)
                }
            
            # 按类型组织分布数据
            distribution_data = {
                'age': {},
                'gender': {},
                'education': {}
            }
            
            for dist in profile_dist:
                distribution_data[dist.profile_type][str(dist.category_value)] = {
                    'count': dist.user_count,
                    'percentage': float(dist.percentage)
                }
            
            # 3. 获取GPT过滤后的共现词数据
            cooccurrence = db.query(models.FilteredSearchVolumeAnalysis).filter(
                models.FilteredSearchVolumeAnalysis.seed_analysis_id == analysis_id
            ).all()
            
            # 获取共现词的GPT分类结果
            cooccurrence_classified = {
                'brand': [],
                'attribute': [],
                'function': [],
                'scenario': [],
                'demand': [],
                'other': []
            }
            
            for word in cooccurrence:
                # 直接使用表中的category字段
                category = word.category  # 分类直接存储在主表中
                if category in cooccurrence_classified:
                    cooccurrence_classified[category].append({
                        'keyword': word.mediator_keyword,
                        'count': word.cooccurrence_volume,
                        'weight': float(word.weight),
                        'confidence': float(word.gpt_confidence),
                        'total_volume': word.mediator_total_volume,
                        'ratio': float(word.cooccurrence_ratio)
                    })
            
            # 4. 获取GPT过滤后的竞争词数据
            competitors = db.query(models.FilteredCompetitorKeywords).filter(
                models.FilteredCompetitorKeywords.seed_analysis_id == analysis_id
            ).all()
            
            # 获取竞争词的GPT分类结果
            competitors_classified = {
                'direct': [],
                'substitute': [],
                'related': [],
                'scenario': [],
                'other': []
            }
            
            for comp in competitors:
                # 直接使用表中的competition_type字段
                category = comp.competition_type  # 竞争类型直接存储在主表中
                if category in competitors_classified:
                    competitors_classified[category].append({
                        'keyword': comp.competitor_keyword,
                        'score': float(comp.weighted_competition_score),
                        'base_score': float(comp.base_competition_score),
                        'volume': comp.cooccurrence_volume,
                        'confidence': float(comp.gpt_confidence)
                    })
            
            # 按权重/得分排序并添加更多有用信息
            for category in cooccurrence_classified:
                cooccurrence_classified[category].sort(key=lambda x: x['weight'], reverse=True)
                cooccurrence_classified[category] = [{
                    **item,
                    'category': category,
                    'ratio_formatted': f"{item['ratio']:.2f}%",
                    'weight_formatted': f"{item['weight']:.2f}"
                } for item in cooccurrence_classified[category][:10]]
            
            for category in competitors_classified:
                competitors_classified[category].sort(key=lambda x: x['score'], reverse=True)
                competitors_classified[category] = [{
                    **item,
                    'type': category,
                    'score_formatted': f"{item['score']:.2f}%",
                    'base_score_formatted': f"{item['base_score']:.2f}%"
                } for item in competitors_classified[category][:10]]
            
            # 添加数据映射说明
            mapping_info = """
数据说明：
1. 年龄分布映射：
   - 0: 未知年龄
   - 1: 0-18岁
   - 2: 19-23岁
   - 3: 24-30岁
   - 4: 31-40岁
   - 5: 41-50岁
   - 6: 51岁以上

2. 性别映射：
   - 0: 未知性别
   - 1: 男性
   - 2: 女性

3. 教育程度映射：
   - 0: 未知学历
   - 1: 博士
   - 2: 硕士
   - 3: 大学生
   - 4: 高中
   - 5: 初中
   - 6: 小学

注意：在分布数据中，category_value 对应上述映射值。
"""

            # 首先定义系统提示词
            system_prompt = """你是一个资深的市场分析专家，擅长用户洞察、市场策略和品牌营销。
请基于数据提供深度的市场洞察和具体可行的策略建议。

在解读用户画像数据时，请注意：
1. 年龄分布采用分段方式（0=未知，1=0-18岁，2=19-23岁，3=24-30岁，4=31-40岁，5=41-50岁，6=51岁以上）
2. 性别编码为：0=未知，1=男性，2=女性
3. 教育程度编码为：0=未知，1=博士，2=硕士，3=大学生，4=高中，5=初中，6=小学

你的分析应该：
1. 严格基于提供的数据，正确解读数据含义
2. 提供具体可执行的建议
3. 考虑行业特点和市场环境
4. 注重实用性和可操作性"""

            # 构建用户提示词
            prompt_parts = []
            prompt_parts.append("作为一个市场分析专家，请基于以下全面的数据提供详细的市场洞察和营销建议。\n")
            prompt_parts.append(f"搜索关键词：{keyword}\n")
            
            # 添加数据映射说明
            prompt_parts.append(mapping_info)
            
            # 用户画像部分
            prompt_parts.append("\n1. 用户画像数据：")
            if demographics:
                prompt_parts.append(f"用户规模：{demographics['total_users']}")
                prompt_parts.append("用户特征：")
                prompt_parts.append(f"- 平均年龄：{demographics['avg_age']:.1f} (参考年龄映射)")
                prompt_parts.append(f"- 性别比例：男性 {demographics['male_ratio']:.1f}%, 女性 {demographics['female_ratio']:.1f}%")
                prompt_parts.append(f"- 平均教育水平：{demographics['avg_education']:.1f} (参考教育程度映射)")
                
                prompt_parts.append("\n详细分布数据（请根据上述映射关系解读数据）：")
                prompt_parts.append(json.dumps(distribution_data, ensure_ascii=False, indent=2))
            
            # 竞争分析部分
            prompt_parts.append("\n2. 竞争分析数据：")
            prompt_parts.append(json.dumps(competitors_classified, ensure_ascii=False, indent=2))
            
            # 共现词分析部分
            prompt_parts.append("\n3. 共现词分析：")
            prompt_parts.append(json.dumps(cooccurrence_classified, ensure_ascii=False, indent=2))
            
            # 分析要求部分
            prompt_parts.append("""
请提供以下方面的深度分析：

1. 目标用户分析
   - 核心用户群体画像
   - 用户的消费能力和消费倾向
   - 用户的生活方式和价值观

2. 市场竞争分析
   - 主要竞争对手
   - 竞争优势和劣势
   - 市场机会和威胁

3. 用户需求洞察
   - 核心需求点
   - 潜在需求机会
   - 需求痛点

4. 营销策略建议
   - 产品定位和差异化策略
   - 目标市场选择
   - 营销渠道组合
   - 营销内容方向
   - 促销策略建议

5. 发展建议
   - 产品优化方向
   - 品牌建设建议
   - 市场拓展机会

请以结构化的方式输出分析结果，并尽可能提供具体、可执行的建议。""")
            
            # 合并提示词
            prompt = "\n".join(prompt_parts)
            logger.info("提示词构建完成")
            
            # 打印完整的提示词用于调试
            print("\n" + "="*50)
            print("系统提示词:")
            print("="*50)
            print(system_prompt)
            print("\n" + "="*50)
            print("用户提示词:")
            print("="*50)
            print(prompt)
            print("="*50 + "\n")
            
            # 也记录到日志文件中
            logger.debug("System Prompt:\n%s", system_prompt)
            logger.debug("User Prompt:\n%s", prompt)
            
            # 调用GPT API
            logger.info("调用GPT API进行市场洞察分析...")
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": system_prompt
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            insights = response.choices[0].message.content
            
            # 保存洞察结果到数据库
            market_insight = models.MarketInsight(
                seed_analysis_id=analysis_id,
                content=insights
            )
            db.add(market_insight)
            db.commit()
            
            logger.info("市场洞察分析完成并保存到数据库")
            return insights
            
        except Exception as e:
            logger.error(f"市场洞察分析失败: {str(e)}")
            return f"市场洞察生成失败: {str(e)}"