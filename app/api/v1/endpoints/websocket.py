from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List
from app.core.logger import logger
import json
import asyncio
import numpy as np

def convert_to_json_serializable(obj):
    """转换数据为JSON可序列化格式"""
    if isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.float64, np.float32)):
        return float(obj)
    if isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [convert_to_json_serializable(i) for i in obj]
    return obj

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.heartbeat_interval = 30
        self.heartbeat_tasks: Dict[int, Dict[WebSocket, asyncio.Task]] = {}

    async def connect(self, analysis_id: int, websocket: WebSocket):
        """建立新的WebSocket连接"""
        try:
            await websocket.accept()
            
            # 初始化连接列表
            if analysis_id not in self.active_connections:
                self.active_connections[analysis_id] = []
            self.active_connections[analysis_id].append(websocket)
            
            # 初始化心跳任务字典
            if analysis_id not in self.heartbeat_tasks:
                self.heartbeat_tasks[analysis_id] = {}
            
            # 创建并存储心跳任务
            task = asyncio.create_task(self._heartbeat(analysis_id, websocket))
            self.heartbeat_tasks[analysis_id][websocket] = task
            
            logger.info(f"WebSocket connected for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error in connect: {str(e)}")
            await self.disconnect(analysis_id, websocket)
            raise HTTPException(status_code=500, detail=str(e))

    async def _heartbeat(self, analysis_id: int, websocket: WebSocket):
        """每个连接的心跳处理"""
        try:
            while True:
                try:
                    await websocket.send_json({"type": "heartbeat"})
                    await asyncio.sleep(self.heartbeat_interval)
                except Exception as e:
                    logger.error(f"Heartbeat send failed: {str(e)}")
                    break
        except asyncio.CancelledError:
            logger.info(f"Heartbeat task cancelled for analysis {analysis_id}")
        except Exception as e:
            logger.error(f"Heartbeat error for analysis {analysis_id}: {str(e)}")
        finally:
            await self.disconnect(analysis_id, websocket)

    async def disconnect(self, analysis_id: int, websocket: WebSocket = None):
        """断开特定的WebSocket连接"""
        try:
            if websocket and analysis_id in self.active_connections:
                # 移除连接
                if websocket in self.active_connections[analysis_id]:
                    self.active_connections[analysis_id].remove(websocket)
                
                # 取消并清理心跳任务
                if analysis_id in self.heartbeat_tasks and websocket in self.heartbeat_tasks[analysis_id]:
                    task = self.heartbeat_tasks[analysis_id][websocket]
                    if not task.done():
                        task.cancel()
                    del self.heartbeat_tasks[analysis_id][websocket]
                
                try:
                    await websocket.close()
                except Exception as e:
                    logger.debug(f"Error closing websocket: {str(e)}")
                
                # 如果没有更多连接，清理数据结构
                if not self.active_connections[analysis_id]:
                    del self.active_connections[analysis_id]
                    if analysis_id in self.heartbeat_tasks:
                        del self.heartbeat_tasks[analysis_id]
                
                logger.info(f"WebSocket disconnected for analysis {analysis_id}")
                
        except Exception as e:
            logger.error(f"Error in disconnect: {str(e)}", exc_info=True)

    async def send_progress(self, analysis_id: int, data: dict):
        """向所有相关连接发送进度"""
        if analysis_id in self.active_connections:
            # 转换数据为JSON可序列化格式
            data = convert_to_json_serializable(data)
            data["type"] = "progress"
            
            # 发送进度消息
            failed_connections = []
            for websocket in self.active_connections[analysis_id][:]:
                try:
                    # 如果是完成或错误消息，确保这是最后发送的消息
                    if data.get("stage") in ["completed", "error"]:
                        # 先发送一个最终的进度更新
                        final_progress = {
                            "type": "progress",
                            "stage": data["stage"],
                            "percent": 100,
                            "message": "分析已完成" if data["stage"] == "completed" else "分析出错",
                            "details": data.get("details", {})
                        }
                        await websocket.send_json(final_progress)
                        
                        # 添加短暂延迟确保消息发送完成
                        await asyncio.sleep(0.5)
                        
                        # 取消心跳任务
                        if analysis_id in self.heartbeat_tasks and websocket in self.heartbeat_tasks[analysis_id]:
                            task = self.heartbeat_tasks[analysis_id][websocket]
                            if not task.done():
                                task.cancel()
                        
                        # 关闭连接
                        logger.info(f"Analysis {analysis_id} {data['stage']}, closing connection")
                        await websocket.close(code=1000)  # 1000 表示正常关闭
                        failed_connections.append(websocket)
                    else:
                        # 对于普通进度消息，直接发送
                        await websocket.send_json(data)
                        
                except Exception as e:
                    logger.error(f"Error sending progress: {str(e)}")
                    failed_connections.append(websocket)
            
            # 清理失败或已完成的连接
            for websocket in failed_connections:
                await self.disconnect(analysis_id, websocket)

manager = ConnectionManager()

@router.websocket("/ws/analysis/{analysis_id}")
async def websocket_endpoint(websocket: WebSocket, analysis_id: int):
    """WebSocket端点"""
    logger.info(f"New WebSocket connection request for analysis {analysis_id}")
    
    try:
        await manager.connect(analysis_id, websocket)
        
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received message: {data}")
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected normally for analysis {analysis_id}")
                break
            except Exception as e:
                logger.error(f"Error in websocket communication: {str(e)}")
                break
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await manager.disconnect(analysis_id, websocket) 