from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
from app.core.logger import logger

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, analysis_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[analysis_id] = websocket
        logger.info(f"WebSocket connected for analysis {analysis_id}")

    def disconnect(self, analysis_id: int):
        if analysis_id in self.active_connections:
            del self.active_connections[analysis_id]
            logger.info(f"WebSocket disconnected for analysis {analysis_id}")

    async def send_progress(self, analysis_id: int, data: dict):
        if analysis_id in self.active_connections:
            try:
                await self.active_connections[analysis_id].send_json(data)
            except Exception as e:
                logger.error(f"Error sending progress: {str(e)}")
                self.disconnect(analysis_id)

manager = ConnectionManager()

@router.websocket("/ws/analysis/{analysis_id}")
async def websocket_endpoint(websocket: WebSocket, analysis_id: int):
    await manager.connect(analysis_id, websocket)
    try:
        while True:
            # 保持连接活跃
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(analysis_id) 