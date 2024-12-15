from app.core.database import SessionLocal
from app import crud, models
from keyword_analysis import KeywordAnalyzer
import mysql.connector
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logger import logger, log_memory_usage
import pandas as pd
import os
import numpy as np
from app.api.v1.endpoints.websocket import manager
import asyncio
from concurrent.futures import ThreadPoolExecutor
import gc

# 创建线程池
thread_pool = ThreadPoolExecutor(max_workers=4)

def convert_numpy_int64(value):
    """转换numpy.int64为Python原生int类型"""
    if isinstance(value, np.int64):
        return int(value)
    if isinstance(value, np.float64):
        return float(value)
    return value

async def run_analysis(keyword: str, analysis_id: int):
    """运行关键词分析并保存结果"""
    logger.info(f"开始执行分析任务 ID: {analysis_id}, 关键词: {keyword}")
    log_memory_usage()
    
    db_conn = None
    analyzer = None
    try:
        # 更新状态为处理中
        db_url = settings.DATABASE_URL
        db_config = {
            'host': db_url.split('@')[1].split('/')[0],
            'user': db_url.split('://')[1].split(':')[0],
            'password': db_url.split(':')[2].split('@')[0],
            'database': db_url.split('/')[-1]
        }
        db_conn = mysql.connector.connect(**db_config)
        cursor = db_conn.cursor()
        
        cursor.execute("""
            UPDATE seed_keyword_analysis 
            SET status = 'processing'
            WHERE id = %s
        """, (analysis_id,))
        db_conn.commit()
        
        # 创建分析器实例
        analyzer = KeywordAnalyzer(
            keyword,
            analysis_id=analysis_id,
            db_conn=db_conn  # 传入数据库连接
        )
        
        # 设置进度回调
        async def progress_callback(data: dict):
            await manager.send_progress(analysis_id, data)
        
        analyzer.set_progress_callback(progress_callback)
        
        # 报告初始化进度
        await progress_callback({
            "stage": "initializing",
            "percent": 0,
            "message": "正在初始化分析...",
            "details": {"keyword": keyword}
        })
        
        # 直接调用异步的load_data方法
        await analyzer.load_data()
        
        # 运行分析的各个阶段
        related_words = await analyzer.find_related_keywords()
        mediator_df = await analyzer.calculate_search_volume(related_words)
        await analyzer.find_competitors(mediator_df)
        
        # 报告完成进度
        await progress_callback({
            "stage": "completed",
            "percent": 100,
            "message": "分析完成",
            "details": {
                "keyword": keyword,
                "total_volume": analyzer.df["Count"].sum(),
                "seed_volume": analyzer.seed_volume
            }
        })
        
        logger.info(f"分析任务完成 ID: {analysis_id}")
        log_memory_usage()
        
        # 保存结果到数据库
        try:
            # 更新分析结果和状态
            total_volume = convert_numpy_int64(analyzer.df["Count"].sum())
            seed_volume = convert_numpy_int64(analyzer.seed_volume)
            seed_ratio = round(seed_volume/total_volume*100, 2)
            
            cursor.execute("""
                UPDATE seed_keyword_analysis 
                SET status = 'completed',
                    total_search_volume = %s,
                    seed_search_volume = %s,
                    seed_search_ratio = %s
                WHERE id = %s
            """, (total_volume, seed_volume, seed_ratio, analysis_id))
            
            # 2. 保存共现关键词
            result_dir = 'result'
            related_file = os.path.join(result_dir, f'related_to_{keyword}.txt')
            if os.path.exists(related_file):
                with open(related_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[4:]:  # 跳过前4行说明文字
                        if '\t\t' in line:
                            kw, count = line.strip().split('\t\t')
                            cursor.execute("""
                                INSERT INTO cooccurrence_keywords 
                                (seed_analysis_id, keyword, cooccurrence_count)
                                VALUES (%s, %s, %s)
                            """, (analysis_id, kw, int(count)))
            
            # 3. 保存搜索量分析结果
            volume_file = os.path.join(result_dir, f'search_volume_{keyword}.csv')
            if os.path.exists(volume_file):
                volume_df = pd.read_csv(volume_file, skiprows=5)
                for _, row in volume_df.iterrows():
                    cursor.execute("""
                        INSERT INTO search_volume_analysis 
                        (seed_analysis_id, mediator_keyword, cooccurrence_volume, 
                         mediator_total_volume, cooccurrence_ratio, weight)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        analysis_id,
                        row['中介关键词'],
                        convert_numpy_int64(row['共现搜索量']),
                        convert_numpy_int64(row['中介词总搜索量']),
                        float(row['共现比例']),
                        float(row['权重'])
                    ))
            
            # 4. 保存竞争关键词
            competitor_file = os.path.join(result_dir, f'competitors_{keyword}.csv')
            if os.path.exists(competitor_file):
                competitor_df = pd.read_csv(competitor_file, skiprows=3)
                competitor_df = competitor_df.head(30)  # 只取前30名
                for _, row in competitor_df.iterrows():
                    cursor.execute("""
                        INSERT INTO competitor_keywords 
                        (seed_analysis_id, competitor_keyword, mediator_keywords,
                         cooccurrence_volume, base_competition_score, weighted_competition_score)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        analysis_id,
                        row['竞争性关键词'],
                        row['中介关键词'],
                        convert_numpy_int64(row['共现搜索量']),
                        float(row['基础竞争度']),
                        float(row['加权竞争度'])
                    ))
            
            db_conn.commit()
            logger.info("Analysis results saved to database successfully")
            
        except Exception as e:
            db_conn.rollback()
            await progress_callback({
                "stage": "error",
                "percent": 0,
                "message": f"保存结果时出错: {str(e)}",
                "details": {"error": str(e)}
            })
            raise
            
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        log_memory_usage()
        if db_conn and db_conn.is_connected():
            cursor = db_conn.cursor()
            cursor.execute("""
                UPDATE seed_keyword_analysis 
                SET status = 'failed',
                    error_message = %s
                WHERE id = %s
            """, (str(e), analysis_id))
            db_conn.commit()
            
        # 发送错误进度
        await manager.send_progress(analysis_id, {
            "stage": "error",
            "percent": 0,
            "message": f"分析失败: {str(e)}",
            "details": {"error": str(e)}
        })
        raise
    finally:
        if analyzer:
            analyzer.cleanup()  # 清理资源
        if db_conn and db_conn.is_connected():
            cursor.close()
            db_conn.close()
        gc.collect()  # 强制垃圾回收