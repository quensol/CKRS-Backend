from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict
from app.core.logger import logger
import json
import asyncio

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, analysis_id: int, websocket: WebSocket):
        try:
            logger.info(f"Attempting to connect WebSocket for analysis {analysis_id}")
            await websocket.accept()
            self.active_connections[analysis_id] = websocket
            logger.info(f"WebSocket connected for analysis {analysis_id}")
            
            # 发送测试消息
            test_messages = [
                {
                    "stage": "initializing",
                    "percent": 0,
                    "message": "开始初始化...",
                    "details": {"status": "starting"}
                },
                {
                    "stage": "processing",
                    "percent": 50,
                    "message": "正在处理...",
                    "details": {"status": "running"}
                },
                {
                    "stage": "completed",
                    "percent": 100,
                    "message": "处理完成",
                    "details": {"status": "done"}
                }
            ]
            
            for msg in test_messages:
                await asyncio.sleep(2)
                await self.send_progress(analysis_id, msg)
        except Exception as e:
            logger.error(f"Error in connect: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def disconnect(self, analysis_id: int):
        if analysis_id in self.active_connections:
            try:
                await self.active_connections[analysis_id].close()
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")
            finally:
                del self.active_connections[analysis_id]
                logger.info(f"WebSocket disconnected for analysis {analysis_id}")

    async def send_progress(self, analysis_id: int, data: dict):
        if analysis_id in self.active_connections:
            try:
                await self.active_connections[analysis_id].send_json(data)
                logger.info(f"Sent progress update: {data}")
            except Exception as e:
                logger.error(f"Error sending progress: {str(e)}")
                await self.disconnect(analysis_id)

manager = ConnectionManager()

@router.websocket("/ws/analysis/{analysis_id}", name="ws_analysis")
async def websocket_endpoint(
    websocket: WebSocket, 
    analysis_id: int
):
    logger.info(f"New WebSocket connection request for analysis {analysis_id}")
    # 手动处理 CORS
    origin = websocket.headers.get("origin", "")
    logger.info(f"Connection request from origin: {origin}")
    
    try:
        await manager.connect(analysis_id, websocket)
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received message: {data}")
            except WebSocketDisconnect:
                await manager.disconnect(analysis_id)
                break
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        if analysis_id in manager.active_connections:
            await manager.disconnect(analysis_id) 