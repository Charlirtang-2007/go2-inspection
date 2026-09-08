# app/utils/websocket_manager.py
# 网络通信
from fastapi import WebSocket
from typing import List, Dict, Any
import json
import asyncio

class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_data: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_data[websocket] = {"subscribed": []}
        print(f"✅ WebSocket 连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.connection_data.pop(websocket, None)
        print(f"❌ WebSocket 连接数: {len(self.active_connections)}")
    
    async def send_json(self, websocket: WebSocket, data: dict):
        """发送 JSON 到指定客户端"""
        try:
            await websocket.send_text(json.dumps(data))
        except:
            pass
    
    async def broadcast(self, message: dict, topic: str = None):
        """广播消息到所有连接的客户端"""
        for connection in self.active_connections[:]:
            if topic and topic not in self.connection_data.get(connection, {}).get("subscribed", []):
                continue
            await self.send_json(connection, message)

manager = ConnectionManager()