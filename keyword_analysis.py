import pandas as pd
import os
from collections import defaultdict
from tqdm import tqdm
import threading
from queue import Queue
import sys
import mysql.connector
import asyncio
import time
from app.core.logger import logger, log_memory_usage
import gc
import numpy as np
import re

# 全局变量
print_queue = Queue()
df_cache = {
    'data': None,
    'last_access': 0,
    'keyword_index': None
}
df_lock = threading.Lock()

class KeywordAnalyzer:
    def __init__(self, seed_keyword, csv_file='query_list_3.csv', user_query_file='user_queries_filtered.utf8', analysis_id=None, db_conn=None):
        self.seed_keyword = seed_keyword
        self.csv_file = csv_file
        self.df = None
        self.seed_queries = None
        self.result_dir = 'result'
        self.progress_callback = None
        self.user_query_file = user_query_file
        self.user_df = None
        self._query_cache = {}
        self._profile_cache = {}
        
        # 添加数据库相关属性
        self.analysis_id = analysis_id
        self.db_conn = db_conn
        
        # 创建结果目录
        if not os.path.exists(self.result_dir):
            os.makedirs(self.result_dir)
            
        # 启动打印线程
        self.print_thread = threading.Thread(target=self._print_worker, daemon=True)
        self.print_thread.start()

    def _safe_print(self, *args, **kwargs):
        """线程安全的打印函数"""
        print_queue.put((args, kwargs))

    def _print_worker(self):
        """处理打印队列的工作线程"""
        while True:
            args, kwargs = print_queue.get()
            if args is None:
                break
            print(*args, **kwargs)
            print_queue.task_done()

    async def load_data(self):
        """加载并预处理数据"""
        logger.info("开始加载数据")
        log_memory_usage()
        
        with df_lock:
            current_time = time.time()
            
            # 检查是否需要重新加载数据
            if df_cache['data'] is None or (current_time - df_cache['last_access']) > 3600:  # 1小时过期
                self._safe_print('读取数据文件...')
                await self.report_progress(
                    "initializing",
                    10,
                    "正在读取数据文件...",
                    {"step": "reading_file"}
                )
                
                # 读取CSV文件
                df = pd.read_csv(self.csv_file)
                df = df.dropna(subset=['Keyword'])
                df['Keyword'] = df['Keyword'].astype(str)
                df['words'] = df['Keyword'].str.split()
                
                # 创建关键词索引
                keyword_index = defaultdict(list)
                total_rows = len(df)
                for idx, words in enumerate(df['words']):
                    if isinstance(words, list):
                        for word in words:
                            keyword_index[word].append(idx)
                
                # 更新缓存
                df_cache['data'] = df
                df_cache['keyword_index'] = keyword_index
                df_cache['last_access'] = current_time
                
                logger.info("数据已重新加载到缓存")
            else:
                logger.info("使用缓存的数据")
                df_cache['last_access'] = current_time
            
            # 使用缓存的数据
            self.df = df_cache['data']
            self.keyword_index = df_cache['keyword_index']
            
            # 获取种子关键词相关的数据
            self.seed_indices = self.keyword_index[self.seed_keyword]
            self.seed_queries = self.df.loc[self.df.index[self.seed_indices]].index
            self.seed_volume = self.df.loc[self.df.index[self.seed_indices], 'Count'].sum()
            
            # 加载用户查询数据
            logger.info("加载用户查询数据")
            try:
                # 使用制表符分隔符读取数据
                self.user_df = pd.read_csv(
                    self.user_query_file,
                    sep='\t',  # 指定制表符分隔
                    names=['ID', 'age', 'gender', 'education', 'query'],  # 指定列名
                    encoding='utf-8',  # 指定编码
                    dtype={  # 指定数据类型
                        'ID': int,
                        'age': int,
                        'gender': int,
                        'education': int,
                        'query': str
                    }
                )
                
                # 处理空值
                self.user_df['query'] = self.user_df['query'].fillna('')
                
                # 预计算数值列的numpy数组
                self.user_arrays = {
                    'age': self.user_df['age'].to_numpy(dtype=np.int32),
                    'gender': self.user_df['gender'].to_numpy(dtype=np.int32),
                    'education': self.user_df['education'].to_numpy(dtype=np.int32)
                }
                
                logger.info(f"成功加载用户查询数据，共 {len(self.user_df)} 条记录")
                
            except Exception as e:
                logger.error(f"加载用户查询数据失败: {str(e)}")
                raise

    def cleanup(self):
        """清理资源"""
        self.df = None
        self.seed_queries = None
        self.keyword_index = None
        gc.collect()  # 强制垃圾回收

    def _get_keyword_mask(self, keyword):
        """使用索引快速获取包含关键词的记录"""
        indices = self.keyword_index.get(keyword, [])
        return self.df.index.isin(indices)

    def set_progress_callback(self, callback):
        """设置进度回���函数"""
        self.progress_callback = callback

    async def report_progress(self, stage: str, percent: int, message: str, details: dict = None):
        """报告进度"""
        if self.progress_callback:
            progress_data = {
                "stage": stage,
                "percent": percent,
                "message": message,
                "details": details or {}
            }
            await self.progress_callback(progress_data)

    async def find_related_keywords(self):
        """查找中介关键词"""
        logger.info("开始查找中介关键词")
        log_memory_usage()
        
        # 获取包含种子关键词的查询
        seed_mask = self.df['words'].apply(lambda x: self.seed_keyword in x)
        seed_queries = self.df[seed_mask]
        
        # 统计共现词
        cooccurrence = defaultdict(int)
        total_queries = len(seed_queries)
        for idx, (_, row) in enumerate(seed_queries.iterrows()):
            words = row['words']
            count = row['Count']
            for word in words:
                if word != self.seed_keyword:
                    cooccurrence[word] += count
            
            # 报告进度
            if idx % 50 == 0:  # 改为每50条更新一次
                percent = int((idx + 1) / total_queries * 100)
                await self.report_progress(
                    "analyzing_cooccurrence",
                    percent,
                    f"正在分析共现词 ({idx + 1}/{total_queries})",
                    {
                        "current": idx + 1,
                        "total": total_queries,
                        "found_words": len(cooccurrence)
                    }
                )
        
        # 排序并保存结果
        sorted_words = sorted(cooccurrence.items(), key=lambda x: x[1], reverse=True)
        output_file = os.path.join(self.result_dir, f'related_to_{self.seed_keyword}.txt')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f'与"{self.seed_keyword}"共现的关键词(共现次数 >= 2)：\n')
            f.write('-' * 40 + '\n')
            f.write('关键词\t\t共现次数\n')
            f.write('-' * 40 + '\n')
            for word, count in sorted_words:
                if count >= 2:
                    f.write(f'{word}\t\t{count}\n')
        
        # 在方法结束前发送100%完成的进度
        await self.report_progress(
            "analyzing_cooccurrence",
            100,
            f"共现词分析完成 (共发现 {len(cooccurrence)} 个关键词)",
            {
                "current": total_queries,
                "total": total_queries,
                "found_words": len(cooccurrence)
            }
        )
        
        logger.info("中介关键词分析完成")
        log_memory_usage()
        return sorted_words

    async def calculate_search_volume(self, related_words):
        """计算搜索量"""
        logger.info("开始计算搜索量")
        log_memory_usage()
        
        # 发送阶段开始的进度信息
        await self.report_progress(
            "calculating_volume",
            0,
            "开始计算搜索量...",
            {
                "step": "initializing",
                "total_words": len(related_words)
            }
        )
        
        # 定义过滤规则（与竞争词使用相同的规则）
        def is_valid_mediator(word):
            """判断中介词是否有效"""
            # 过滤纯数字
            if word.isdigit():
                return False
            
            # 过滤单字母和单字符
            if len(word) == 1:
                return False
            
            # 过滤中文单字
            if len(word.encode('utf-8')) <= 3:
                return False
            
            # 过滤常见无意义词
            stop_words = {'的', '了', '和', '与', '及', '或', '在', '中', '有', '个',
                         'the', 'a', 'an', 'of', 'to', 'and', 'or', 'for', 'in',
                         '最', '多', '个', '为', '等', '从', '到', '着', '给', '让',
                         '年', '月', '日', '号', '价', '价格', '多少', '怎么', '如何',
                         '什么', '哪里', '哪个', '这个', '那个', '一个', '这些', '那些',
                         '图片', '图', '照片', '大全', '介绍', '说明', '简介', '资料',
                         '官网', '网站', '专卖', '专卖店', '店', '商店', '网店', '旗舰店',
                         '官方', '正品', '专柜', '实体店', '直营店', '加盟店', '经销商',
                         '哪家', '在哪', '地址', '电话', '联系', '咨询', '售后', '服务',
                         '价位', '多少钱', '贵不贵', '便宜', '实惠', '划算', '性价比'}
            
            if word in stop_words:
                return False
            
            # 过滤包含特定字符的词
            invalid_chars = {'?', '？', '!', '！', '。', '，', ',', '.', '、',
                            '(', ')', '（', '）', '[', ']', '【', '】',
                            '+', '-', '*', '/', '=', '|', '\\'}
            if any(char in word for char in invalid_chars):
                return False
            
            # 过滤纯英文介词、冠词等
            english_stop_words = {'the', 'a', 'an', 'of', 'to', 'and', 'or', 'for', 'in', 'on', 'at'}
            if word.lower() in english_stop_words:
                return False
            
            # 过滤常见时间词
            time_words = {'今天', '明天', '昨天', '上午', '下午', '晚上', '早上',
                         '周一', '周二', '周三', '周四', '周五', '周六', '周日',
                         '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日',
                         '月份', '年份', '季度'}
            if word in time_words:
                return False
            
            # 过滤常见数量词和单位
            unit_words = {'个', '件', '只', '条', '张', '台', '部', '款', '种',
                         '千克', '公斤', '克', '斤', '两', '升', '毫升', '米', '厘米',
                         '元', '块', '角', '分'}
            if word in unit_words:
                return False
            
            return True
        
        results = []
        # 只保留两个过滤件：
        # 1. 共现次数>=5
        # 2. 通过停用词等规则的有效性检查
        related_keywords = []
        filtered_count = 0
        for word, count in related_words:
            if count >= 5 and is_valid_mediator(word):
                related_keywords.append((word, count))
            else:
                filtered_count += 1
        
        self._safe_print(f'过滤掉 {filtered_count} 个无效中介关键词')
        self._safe_print(f'保留 {len(related_keywords)} 个有效中介关键词')
        
        if not related_keywords:
            self._safe_print('未找到符合条件的中介关键词')
            return pd.DataFrame()
        
        # 更新进度信息
        await self.report_progress(
            "calculating_volume",
            0,
            f"开始计算 {len(related_keywords)} 个关键词的搜索量",
            {
                "step": "volume_calculation",
                "total": len(related_keywords),
                "current": 0
            }
        )
        
        # 批量预计算所有中介词的搜索量
        self._safe_print('预计算中介关键词搜索量...')
        related_volumes = {}
        total_keywords = len(related_keywords)
        update_interval = max(1, int(total_keywords * 0.005))  # 每处理0.5%的数据新一次
        
        # 使用tqdm创建进度条，设置动态输出
        progress_bar = tqdm(
            total=total_keywords,
            desc='计算搜索量',
            file=sys.stdout,
            dynamic_ncols=True,  # 动态调整宽度
            leave=True,  # 保留进度条
            position=0   # 固定位置
        )
        
        for idx, (related_keyword, _) in enumerate(related_keywords):
            mask = self._get_keyword_mask(related_keyword)
            related_volumes[related_keyword] = self.df[mask]['Count'].sum()
            
            # 更新进度条
            progress_bar.update(1)
            
            # WebSocket进度推送（频率更高）
            if idx % update_interval == 0 or idx == total_keywords - 1:
                percent = int((idx + 1) / total_keywords * 100)
                await self.report_progress(
                    "calculating_volume",
                    percent,
                    f"计算搜索量中 ({idx + 1}/{total_keywords})",
                    {
                        "step": "volume_calculation",
                        "current": idx + 1,
                        "total": total_keywords,
                        "processed_words": idx + 1
                    }
                )
        
        progress_bar.close()
        
        # 批量处理中介关键词
        results = []
        progress_bar = tqdm(
            total=total_keywords,
            desc='处理数据',
            file=sys.stdout,
            dynamic_ncols=True,
            leave=True,
            position=0
        )
        
        for idx, (related_keyword, both_volume) in enumerate(related_keywords):
            related_volume = related_volumes[related_keyword]
            weight = round(both_volume / self.seed_volume * 100, 4) if self.seed_volume > 0 else 0
            
            results.append({
                '中介关键词': related_keyword,
                '共现搜索量': both_volume,
                '中介词总搜索量': related_volume,
                '共现比例': round(both_volume / related_volume * 100, 2) if related_volume > 0 else 0,
                '权重': weight
            })
            
            # 更新进度条
            progress_bar.update(1)
            
            # WebSocket进度推送（频率更高）
            if idx % update_interval == 0 or idx == total_keywords - 1:
                percent = int((idx + 1) / total_keywords * 100)
                await self.report_progress(
                    "calculating_volume",
                    percent,
                    f"处理搜索量数据 ({idx + 1}/{total_keywords})",
                    {
                        "step": "data_processing",
                        "current": idx + 1,
                        "total": total_keywords,
                        "processed_words": len(results)
                    }
                )
        
        progress_bar.close()
        
        # 发送100%完成进度
        await self.report_progress(
            "calculating_volume",
            100,
            f"搜索量计算完成 (共处理 {len(results)} 个关键词)",
            {
                "step": "completed",
                "total_words": len(results)
            }
        )
        
        if not results:
            self._safe_print('未找到符合条件的中介关键词')
            return pd.DataFrame()
        
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values(['权重', '共现搜索量'], ascending=[False, False])
        output_file = os.path.join(self.result_dir, f'search_volume_{self.seed_keyword}.csv')
        
        self._save_search_volume_results(output_file, results_df)
        logger.info("搜索量计算完成")
        log_memory_usage()
        return results_df
    
    async def analyze_user_profiles(self, competitor_keywords):
        """分析用户画像"""
        logger.info("开始分析用户画像")
        
        try:
            # 1. 先只用种子关键词匹配
            logger.info(f"使用种子关键词 '{self.seed_keyword}' 匹配用户")
            matched_users = self.user_df[
                self.user_df['query'].str.contains(self.seed_keyword, na=False, case=False)
            ]
            
            if len(matched_users) == 0:
                # 2. 如果没有匹配到，再使用竞争关键词扩大范围
                logger.info("种子关键词未匹配到用户，尝试使用竞争关键词")
                competitor_keywords_list = [kw['竞争性关键词'] for kw in competitor_keywords]
                logger.info(f"竞争关键词列表: {competitor_keywords_list[:10]}...")
                
                pattern = '|'.join([self.seed_keyword] + competitor_keywords_list)
                matched_users = self.user_df[
                    self.user_df['query'].str.contains(pattern, na=False, case=False)
                ]
            
            if len(matched_users) == 0:
                logger.warning("未找到匹配的用户数据")
                return None, None
            
            logger.info(f"找到 {len(matched_users)} 个匹配用户")
            
            # 使用numpy进行统计计算
            age_array = matched_users['age'].to_numpy()
            gender_array = matched_users['gender'].to_numpy()
            education_array = matched_users['education'].to_numpy()
            
            # 快速统计
            total_users = len(matched_users)
            age_dist = {i: int(np.sum(age_array == i)) for i in range(7)}
            gender_dist = {i: int(np.sum(gender_array == i)) for i in range(3)}
            education_dist = {i: int(np.sum(education_array == i)) for i in range(7)}
            
            # 计算平均值和比例（排除未知值0）
            valid_ages = age_array[age_array != 0]
            avg_age = float(np.mean(valid_ages)) if len(valid_ages) > 0 else 0
            
            valid_genders = gender_array[gender_array != 0]
            total_known_gender = len(valid_genders)
            male_ratio = (len(valid_genders[valid_genders == 1]) / total_known_gender * 100) if total_known_gender > 0 else 0
            female_ratio = (len(valid_genders[valid_genders == 2]) / total_known_gender * 100) if total_known_gender > 0 else 0
            
            valid_education = education_array[education_array != 0]
            avg_education = float(np.mean(valid_education)) if len(valid_education) > 0 else 0
            
            # 准备返回结果
            profile_stats = {
                'total_users': total_users,
                'avg_age': round(avg_age, 2),
                'male_ratio': round(male_ratio, 2),
                'female_ratio': round(female_ratio, 2),
                'avg_education': round(avg_education, 2)
            }
            
            profile_dist = {
                'age': {str(k): {'count': v, 'percentage': round(v/total_users*100, 2)} 
                       for k, v in age_dist.items()},
                'gender': {str(k): {'count': v, 'percentage': round(v/total_users*100, 2)} 
                          for k, v in gender_dist.items()},
                'education': {str(k): {'count': v, 'percentage': round(v/total_users*100, 2)} 
                             for k, v in education_dist.items()}
            }
            
            logger.info(f"用户画像分析完成: {profile_stats}")
            
            # 如果有数据库连接，保存结果
            if self.db_conn and self.analysis_id:
                try:
                    cursor = self.db_conn.cursor()
                    
                    # 插入统计数据
                    cursor.execute("""
                        INSERT INTO user_profile_statistics 
                        (seed_analysis_id, total_users, avg_age, male_ratio, female_ratio, avg_education)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        self.analysis_id,
                        profile_stats['total_users'],
                        profile_stats['avg_age'],
                        profile_stats['male_ratio'],
                        profile_stats['female_ratio'],
                        profile_stats['avg_education']
                    ))
                    
                    # 插入分布数据
                    distribution_data = []
                    for profile_type, dist in profile_dist.items():
                        for category_value, stats in dist.items():
                            distribution_data.append((
                                self.analysis_id,
                                profile_type,
                                int(category_value),
                                stats['count'],
                                stats['percentage']
                            ))
                    
                    cursor.executemany("""
                        INSERT INTO user_profile_distribution 
                        (seed_analysis_id, profile_type, category_value, user_count, percentage)
                        VALUES (%s, %s, %s, %s, %s)
                    """, distribution_data)
                    
                    self.db_conn.commit()
                    logger.info("用户画像数据已保存到数据库")
                    
                except Exception as e:
                    logger.error(f"保存用户画像数据时出错: {str(e)}")
                    self.db_conn.rollback()
                    raise
            
            return profile_stats, profile_dist
            
        except Exception as e:
            logger.error(f"用户画像分析出错: {str(e)}")
            return None, None

    async def find_competitors(self, mediator_df):
        """分析竞争关键词"""
        logger.info("开始分析竞争关键词")
        log_memory_usage()
        
        if mediator_df.empty:
            self._safe_print('没有有效的中介关键词，跳过竞争关键词分析')
            return
        
        # 定义过滤规则
        def is_valid_competitor(word):
            """判断竞争词是否有效"""
            # 过滤纯数字
            if word.isdigit():
                return False
            
            # 过滤单字母和单字符
            if len(word) == 1:
                return False
            
            # 过滤中文单字
            if len(word.encode('utf-8')) <= 3:
                return False
            
            # 过滤常见无意义词
            stop_words = {'的', '了', '和', '与', '及', '或', '在', '中', '有', '个',
                         'the', 'a', 'an', 'of', 'to', 'and', 'or', 'for', 'in',
                         '最', '多', '个', '为', '等', '从', '到', '着', '给', '让',
                         '年', '月', '日', '号', '价', '价格', '多少', '怎么', '如何',
                         '什么', '哪里', '哪个', '这个', '那个', '一个', '这些', '那些',
                         '图片', '图', '照片', '大全', '介绍', '说明', '简介', '资料',
                         '官网', '网站', '专卖', '专卖店', '店', '商店', '网店', '旗舰店',
                         '官方', '正品', '专柜', '实体店', '直营店', '加盟店', '经销商',
                         '哪家', '在哪', '地址', '电话', '联系', '咨询', '售后', '服务',
                         '价位', '多少钱', '贵不贵', '便宜', '实惠', '划算', '性价比'}
                     
            if word in stop_words:
                return False
            
            # 过滤包含特定字符的词
            invalid_chars = {'?', '？', '!', '！', '。', '，', ',', '.', '、',
                            '(', ')', '（', '）', '[', ']', '【', '】',
                            '+', '-', '*', '/', '=', '|', '\\'}
            if any(char in word for char in invalid_chars):
                return False
            
            # 过滤纯英文介词、冠词等
            english_stop_words = {'the', 'a', 'an', 'of', 'to', 'and', 'or', 'for', 'in', 'on', 'at'}
            if word.lower() in english_stop_words:
                return False
            
            # 过滤常见时间词
            time_words = {'今天', '明天', '昨天', '上午', '下午', '晚上', '早上',
                         '周一', '周二', '周三', '周四', '周五', '周六', '周日',
                         '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日',
                         '月份', '年份', '季度'}
            if word in time_words:
                return False
            
            # 滤常见数量和单位
            unit_words = {'个', '件', '只', '条', '张', '台', '部', '款', '种',
                         '千克', '公斤', '克', '斤', '两', '升', '毫升', '米', '厘米',
                         '元', '块', '角', '分'}
            if word in unit_words:
                return False
            
            return True
        
        # 预计算所有中介词的查询索引
        mediator_indices = {}
        for mediator_keyword in tqdm(mediator_df['中介关键词'], desc='预处理中介词'):
            mediator_indices[mediator_keyword] = set(self.keyword_index[mediator_keyword])
        
        all_competitors = []
        total_mediators = len(mediator_df)
        for idx, (_, row) in enumerate(mediator_df.iterrows()):
            mediator_keyword = row['中介关键词']
            mediator_weight = row['权重']
            
            # 使用预计算的索引
            mediator_idx = list(mediator_indices[mediator_keyword])
            # 使用loc访问DataFrame
            mediator_volume = self.df.loc[self.df.index[mediator_idx], 'Count'].sum()
            
            # 计算共现查询
            seed_mediator_idx = list(set(mediator_idx) & set(self.seed_indices))
            seed_mediator_volume = self.df.loc[self.df.index[seed_mediator_idx], 'Count'].sum()
            
            # 找出竞争查询
            competitor_idx = list(set(mediator_idx) - set(self.seed_indices))
            if not competitor_idx:
                continue
            
            # 统计竞争词
            competitors = defaultdict(int)
            competitor_queries = self.df.loc[self.df.index[competitor_idx]]
            for words, count in zip(competitor_queries['words'], competitor_queries['Count']):
                for word in words:
                    if word != mediator_keyword:
                        competitors[word] += count
            
            # 计算竞争度
            denominator = mediator_volume - seed_mediator_volume
            if denominator <= 0:
                continue
            
            # 在添加竞争词时进行过滤
            for word, cooccurrence in competitors.items():
                if not is_valid_competitor(word):
                    continue
                
                base_competition_score = cooccurrence / denominator
                weighted_competition_score = base_competition_score * (mediator_weight / 100)
                
                all_competitors.append({
                    '竞争性关键词': word,
                    '中介关键词': mediator_keyword,
                    '共现搜索量': cooccurrence,
                    '基础竞争度': round(base_competition_score * 100, 4),
                    '加权竞争度': round(weighted_competition_score * 100, 4)
                })
            
            # 报告进度
            if idx % 5 == 0:  # 每处理5个中介词报告一次进度
                percent = int((idx + 1) / total_mediators * 100)
                await self.report_progress(
                    "analyzing_competitors",
                    percent,
                    f"正在分析竞争关键词 ({idx + 1}/{total_mediators})",
                    {
                        "current": idx + 1,
                        "total": total_mediators,
                        "found_competitors": len(all_competitors)
                    }
                )
        
        self._save_competitor_results(all_competitors)
        logger.info("竞争关键词分析完成")
        log_memory_usage()
        
        # 在完成竞争关键词分析后，进行用户画像分析
        profile_stats, profile_dist = await self.analyze_user_profiles(all_competitors)
        
        return all_competitors  # 返回竞争关键词结果

    def _save_search_volume_results(self, output_file, results_df):
        """保存搜索量结果"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f'种子关键词: {self.seed_keyword}\n')
            f.write(f'总查询量: {self.df["Count"].sum()}\n')
            f.write(f'种子关键词搜索量: {self.seed_volume}\n')
            f.write(f'种子关键词搜索占比: {round(self.seed_volume/self.df["Count"].sum()*100, 2)}%\n')
            f.write('权重说明: 权重 = (共现搜索量/种子关键词搜索量) * 100%\n\n')
        
        results_df.to_csv(output_file, mode='a', index=False)

    def _save_competitor_results(self, all_competitors):
        """保存竞争关键词结果"""
        if not all_competitors:
            self._safe_print('未找到任何竞争性关键词')
            return
            
        results_df = pd.DataFrame(all_competitors)
        summary_df = results_df.groupby('竞争性关键词').agg({
            '共现搜索量': 'sum',
            '基础竞争度': 'mean',
            '加权竞争度': 'mean',
            '中介关键词': lambda x: ', '.join(sorted(set(x)))
        }).reset_index()
        
        summary_df = summary_df.sort_values('加权竞争度', ascending=False)
        output_file = os.path.join(self.result_dir, f'competitors_{self.seed_keyword}.csv')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('竞争度说明:\n')
            f.write('基础竞争度 = 竞争词与中介词的共现量 / (中介词总量 - 种子词与中介词共现量)\n')
            f.write('加权竞争度 = 基础竞争度 * 中介词权重\n\n')
        
        summary_df.to_csv(output_file, mode='a', index=False, encoding='utf-8')
        self._safe_print(f'\n结果已保存至 {output_file}')

    def save_to_database(self, db_connection):
        """保存分析结果到数据库"""
        try:
            cursor = db_connection.cursor()
            
            # 1. 插入种子关键词分析记录
            cursor.execute("""
                INSERT INTO seed_keyword_analysis 
                (seed_keyword, total_search_volume, seed_search_volume, seed_search_ratio)
                VALUES (%s, %s, %s, %s)
            """, (
                self.seed_keyword,
                self.df["Count"].sum(),
                self.seed_volume,
                round(self.seed_volume/self.df["Count"].sum()*100, 2)
            ))
            seed_analysis_id = cursor.lastrowid
            
            # 2. 保存共现关键词
            cooccurrence_data = []
            with open(os.path.join(self.result_dir, f'related_to_{self.seed_keyword}.txt'), 'r', encoding='utf-8') as f:
                for line in f:
                    if '\t\t' in line:
                        keyword, count = line.strip().split('\t\t')
                        cooccurrence_data.append((seed_analysis_id, keyword, int(count)))
            
            cursor.executemany("""
                INSERT INTO cooccurrence_keywords 
                (seed_analysis_id, keyword, cooccurrence_count)
                VALUES (%s, %s, %s)
            """, cooccurrence_data)
            
            # 3. 保存搜索量分析结果
            volume_df = pd.read_csv(os.path.join(self.result_dir, f'search_volume_{self.seed_keyword}.csv'), skiprows=5)
            volume_data = []
            for _, row in volume_df.iterrows():
                volume_data.append((
                    seed_analysis_id,
                    row['中介关键词'],
                    row['共现搜索量'],
                    row['中介词总搜索量'],
                    row['共现比例'],
                    row['权重']
                ))
            
            cursor.executemany("""
                INSERT INTO search_volume_analysis 
                (seed_analysis_id, mediator_keyword, cooccurrence_volume, 
                 mediator_total_volume, cooccurrence_ratio, weight)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, volume_data)
            
            # 4. 保存竞争关键词(前30名)
            competitor_file = os.path.join(self.result_dir, f'competitors_{self.seed_keyword}.csv')
            if os.path.exists(competitor_file):
                competitor_df = pd.read_csv(competitor_file, skiprows=3)
                competitor_df = competitor_df.head(30)  # 只取前30名
                competitor_data = []
                for _, row in competitor_df.iterrows():
                    competitor_data.append((
                        seed_analysis_id,
                        row['竞争性关键词'],
                        row['中介关键词'],
                        row['共现搜索量'],
                        row['基础竞争度'],
                        row['加权竞争度']
                    ))
                
                cursor.executemany("""
                    INSERT INTO competitor_keywords 
                    (seed_analysis_id, competitor_keyword, mediator_keywords,
                     cooccurrence_volume, base_competition_score, weighted_competition_score)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, competitor_data)
            
            db_connection.commit()
            self._safe_print('分析结果已保存到数据库')
            
        except Exception as e:
            db_connection.rollback()
            self._safe_print(f'保存到数据库时发生错误: {str(e)}')
        finally:
            cursor.close()

    async def run(self):
        """运行完整分析流程"""
        logger.info(f"开始分析关键词: {self.seed_keyword}")
        log_memory_usage()
        
        try:
            # 1. 加载数据
            await self.load_data()
            
            # 2. 查找中介关键词
            related_words = await self.find_related_keywords()
            
            # 3. 计算搜索量
            mediator_df = await self.calculate_search_volume(related_words)
            
            # 4. 分析竞争关键词
            await self.find_competitors(mediator_df)
            
            self._safe_print('\n分析完成！所有结果已保存在result目录下')
            
        except Exception as e:
            # 添加错误状态推送
            await self.report_progress(
                "error",
                0,
                f"分析过程出错: {str(e)}",
                {
                    "error": str(e)
                }
            )
            self._safe_print(f'发生错误: {str(e)}')
        finally:
            logger.info("分析流程结束")
            log_memory_usage()
            # 清理资源
            self.df = None
            self.seed_queries = None
            print_queue.put((None, None))
            self.print_thread.join()
            self.cleanup()

    @staticmethod
    def cleanup_cache():
        """清理过期缓存"""
        with df_lock:
            current_time = time.time()
            expired_keys = [
                key for key, (df, timestamp) in df_cache.items()
                if current_time - timestamp > 3600  # 1小时过期
            ]
            for key in expired_keys:
                del df_cache[key]

def clear_memory_cache():
    """清理内存缓存"""
    with df_lock:
        df_cache['data'] = None
        df_cache['keyword_index'] = None
        df_cache['last_access'] = 0
    gc.collect()

async def periodic_cleanup():
    """定期清理内存"""
    while True:
        try:
            await asyncio.sleep(3600)  # 每小时检查一次
            current_time = time.time()
            with df_lock:
                if df_cache['data'] is not None and (current_time - df_cache['last_access']) > 3600:
                    logger.info("清理过期的数据缓存")
                    clear_memory_cache()
        except Exception as e:
            logger.error(f"Periodic cleanup error: {str(e)}")

def main():
    if len(sys.argv) > 1:
        seed_keyword = sys.argv[1]
    else:
        seed_keyword = input('请输入种子关键词: ').strip()
    
    if not seed_keyword:
        print('错误: 关键词不能为空')
        return
        
    analyzer = KeywordAnalyzer(seed_keyword)
    asyncio.run(analyzer.run())

if __name__ == '__main__':
    main() 