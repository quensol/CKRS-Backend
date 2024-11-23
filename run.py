import uvicorn
import asyncio
from keyword_analysis import periodic_cleanup

if __name__ == "__main__":
    # 启动定期清理任务
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    # 启动服务器
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 