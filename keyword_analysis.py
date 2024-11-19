import pandas as pd
import os
from collections import defaultdict
from tqdm import tqdm
from pyhanlp import *
import threading
from queue import Queue
import sys
import mysql.connector

# 全局变量
print_queue = Queue()
df_cache = {}
df_lock = threading.Lock()

class KeywordAnalyzer:
    def __init__(self, seed_keyword, csv_file='query_list_3.csv'):
        self.seed_keyword = seed_keyword
        self.csv_file = csv_file
        self.df = None
        self.seed_queries = None
        self.result_dir = 'result'
        
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

    def load_data(self):
        """加载并预处理数据"""
        if self.df is None:
            self._safe_print('读取数据文件...')
            self.df = pd.read_csv(self.csv_file)
            
            # 移除空值和NaN
            self.df = self.df.dropna(subset=['Keyword'])
            
            # 预先分词并创建查找表
            self._safe_print('预处理数据...')
            # 确保Keyword是字符串类型
            self.df['Keyword'] = self.df['Keyword'].astype(str)
            self.df['words'] = self.df['Keyword'].str.split()
            
            # 创建关键词索引
            self._safe_print('创建关键词索引...')
            self.keyword_index = defaultdict(list)
            for idx, words in enumerate(self.df['words']):
                if isinstance(words, list):  # 确保words是列表
                    for word in words:
                        self.keyword_index[word].append(idx)
            
            # 获取包含种子关键词的查询
            self.seed_indices = self.keyword_index[self.seed_keyword]
            # 使用loc而不是直接用索引
            self.seed_queries = self.df.loc[self.df.index[self.seed_indices]].index
            self.seed_volume = self.df.loc[self.df.index[self.seed_indices], 'Count'].sum()

    def _get_keyword_mask(self, keyword):
        """使用索引快速获取包含关键词的记录"""
        indices = self.keyword_index.get(keyword, [])
        return self.df.index.isin(indices)

    def find_related_keywords(self):
        """查找中介关键词"""
        self._safe_print('开始查找中介关键词...')
        
        # 获取包含种子关键词的查询
        seed_mask = self.df['words'].apply(lambda x: self.seed_keyword in x)
        seed_queries = self.df[seed_mask]
        
        # 统计共现词
        cooccurrence = defaultdict(int)
        for _, row in tqdm(seed_queries.iterrows(), desc='统计共现词'):
            words = row['words']
            count = row['Count']
            for word in words:
                if word != self.seed_keyword:
                    cooccurrence[word] += count
        
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
        
        return sorted_words

    def calculate_search_volume(self, related_words):
        """计算搜索量"""
        self._safe_print('开始计算搜索量...')
        
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
        # 只保留两个过滤条件：
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
        
        # 批量预计算所有中介词的搜索量
        self._safe_print('预计算中介关键词搜索量...')
        related_volumes = {}
        for related_keyword, _ in tqdm(related_keywords):
            mask = self._get_keyword_mask(related_keyword)
            related_volumes[related_keyword] = self.df[mask]['Count'].sum()
        
        # 批量处理中介关键词，不再检查权重阈值
        for related_keyword, both_volume in tqdm(related_keywords, desc='计算搜索量'):
            related_volume = related_volumes[related_keyword]
            weight = round(both_volume / self.seed_volume * 100, 4) if self.seed_volume > 0 else 0
            
            results.append({
                '中介关键词': related_keyword,
                '共现搜索量': both_volume,
                '中介词总搜索量': related_volume,
                '共现比例': round(both_volume / related_volume * 100, 2) if related_volume > 0 else 0,
                '权重': weight
            })
        
        if not results:
            self._safe_print('未找到符合条件的中介关键词')
            return pd.DataFrame()
        
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values(['权重', '共现搜索量'], ascending=[False, False])
        output_file = os.path.join(self.result_dir, f'search_volume_{self.seed_keyword}.csv')
        
        self._save_search_volume_results(output_file, results_df)
        return results_df

    def find_competitors(self, mediator_df):
        """分析竞争关键词"""
        if mediator_df.empty:
            self._safe_print('没有有效的中介关键词，跳过竞争关键词分析')
            return
        
        self._safe_print('开始分析竞争关键词...')
        
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
            
            # 过滤常见数量词和单位
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
        for _, row in tqdm(mediator_df.iterrows(), desc='分析竞争词'):
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
        
        self._save_competitor_results(all_competitors)

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
        
        summary_df.to_csv(output_file, mode='a', index=False)
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

    def run(self):
        """运行完整分析流程"""
        try:
            # 1. 加载数据
            self.load_data()
            
            # 2. 查找中介关键词
            related_words = self.find_related_keywords()
            
            # 3. 计算搜索量
            mediator_df = self.calculate_search_volume(related_words)
            
            # 4. 分析竞争关键词
            self.find_competitors(mediator_df)
            
            self._safe_print('\n分析完成！所有结果已保存在result目录下')
            
        except Exception as e:
            self._safe_print(f'发生错误: {str(e)}')
        finally:
            # 停止打印线程
            print_queue.put((None, None))
            self.print_thread.join()

def main():
    if len(sys.argv) > 1:
        seed_keyword = sys.argv[1]
    else:
        seed_keyword = input('请输入种子关键词: ').strip()
    
    if not seed_keyword:
        print('错误: 关键词不能为空')
        return
        
    analyzer = KeywordAnalyzer(seed_keyword)
    analyzer.run()

if __name__ == '__main__':
    main() 