import uvicorn
import asyncio
from keyword_analysis import periodic_cleanup
import multiprocessing
import logging

# 禁用 watchfiles 的日志输出
logging.getLogger('watchfiles').setLevel(logging.ERROR)

def run_uvicorn():
    """在单独的进程中运行uvicorn服务器"""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_delay=1.0,  # 添加重载延迟
        log_level="info"
    )

async def main():
    """主异步函数"""
    # 创建清理任务
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    # 在单独的进程中启动uvicorn
    server_process = multiprocessing.Process(target=run_uvicorn)
    server_process.start()
    
    try:
        # 保持主事件循环运行
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("正在关闭服务...")
    finally:
        # 取消清理任务
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        
        # 终止服务器进程
        if server_process.is_alive():
            server_process.terminate()
            server_process.join()

if __name__ == "__main__":
    # 设置多进程启动方法
    multiprocessing.freeze_support()
    # 运行主事件循环
    asyncio.run(main()) 