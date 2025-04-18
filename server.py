from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import uuid
import json
import logging
import ssl

# ตั้งค่า logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# ตั้งค่า CORS เพื่ออนุญาตการเชื่อมต่อจากทุก origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# สร้าง SSL context
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain('certs/cert.pem', 'certs/key.pem')  # ต้องมีไฟล์ certificate และ key

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.rooms: Dict[str, Dict[str, WebSocket]] = {}  # {room_id: {client_id: websocket}}
        self.client_rooms: Dict[str, str] = {}  # {client_id: room_id}

    async def connect(self, websocket: WebSocket, client_id: str):
        
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def join_room(self, client_id: str, room_id: str):
        """เพิ่มผู้เล่นเข้าห้อง"""
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
        
        self.rooms[room_id][client_id] = self.active_connections[client_id]
        self.client_rooms[client_id] = room_id
        
        logger.info(f"Client {client_id} joined room {room_id}")
        return room_id

    async def leave_room(self, client_id: str):
        """นำผู้เล่นออกจากห้อง"""
        if client_id not in self.client_rooms:
            return None
            
        room_id = self.client_rooms[client_id]
        if room_id in self.rooms and client_id in self.rooms[room_id]:
            del self.rooms[room_id][client_id]
            del self.client_rooms[client_id]
            
            # ถ้าห้องว่างให้ลบห้อง
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                logger.info(f"Room {room_id} is now empty and removed")
            
            return room_id
        return None

    async def broadcast_to_room(self, message: str, room_id: str, exclude_client_id: Optional[str] = None):
        """ส่งข้อความถึงทุกคนในห้อง"""
        if room_id in self.rooms:
            for client_id, connection in self.rooms[room_id].items():
                if client_id != exclude_client_id:
                    try:
                        await connection.send_text(message)
                    except Exception as e:
                        logger.error(f"Error sending to {client_id}: {e}")
                        self.disconnect(client_id)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str): 
    
    origin = websocket.headers.get("origin")
    print(f"[Server] Received origin from client: {origin}") 
    await websocket.accept() 
    allowed_origins = [
    "http://localhost",
    #"http://127.0.0.1",
    "https://localhost",
    #"https://127.0.0.1",
    #"http://yourdomain.com",
   #"https://yourdomain.com"
    "http://localhost:8000", 
    "https://localhost:8000",
    #"http://192.168.2.69",
    "https://192.168.2.69",
    None
]
    
   
    if origin not in allowed_origins:
        print(f"Rejected connection from: {origin}")
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                logger.info(f"[RECEIVED] From {client_id}: {message}")
                
                if message["type"] == "join_room":
                    room_id = message.get("room_id", "default_room")
                    await manager.join_room(client_id, room_id)
                    
                    # ส่งข้อมูลห้องกลับให้ผู้เล่น
                    room_members = list(manager.rooms[room_id].keys()) if room_id in manager.rooms else []
                    await websocket.send_text(json.dumps({
                        "type": "room_joined",
                        "room_id": room_id,
                        "members": room_members,
                        "your_id": client_id
                    }))
                    
                    # แจ้งเตือนสมาชิกในห้องว่ามีคนใหม่เข้ามา
                    await manager.broadcast_to_room(
                        json.dumps({
                            "type": "new_member",
                            "member_id": client_id,
                            "members": room_members
                        }),
                        room_id,
                        exclude_client_id=client_id
                    )
                    
                elif message["type"] in ["offer", "answer", "ice-candidate"]:
                    target_id = message["target_id"]
                    if target_id in manager.active_connections:
                        await manager.active_connections[target_id].send_text(data)
                    else:
                        logger.warning(f"Target client {target_id} not found")
                
                elif message["type"] == "draw-data":
                    room_id = message.get("room_id")
                    if room_id and room_id in manager.rooms:
                        await manager.broadcast_to_room(
                            json.dumps({
                                "type": "draw-data",
                                "data": message["data"],
                                "sender_id": message["sender_id"],
                                "room_id": room_id
                            }),
                                room_id,
                                exclude_client_id=message["sender_id"]
                             )
                elif message["type"] == "sync_timer":
                    room_id = message.get("room_id")
                    if room_id and room_id in manager.rooms:
                        await manager.broadcast_to_room(
                            json.dumps({
                                "type": "start_timer",
                                "time": message["duration"]
                            }),
                                room_id
                            )        
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from {client_id}")
            except KeyError as e:
                logger.error(f"Missing key in message from {client_id}: {e}")

    except WebSocketDisconnect:
        logger.info(f"[DISCONNECT] {client_id} disconnected")
        room_id = await manager.leave_room(client_id)
        manager.disconnect(client_id)
        
        if room_id:
            # แจ้งเตือนสมาชิกในห้องว่ามีคนออกไป
            room_members = list(manager.rooms[room_id].keys()) if room_id in manager.rooms else []
            await manager.broadcast_to_room(
                json.dumps({
                    "type": "member_left",
                    "member_id": client_id,
                    "members": room_members
                }),
                room_id
            )

@app.get("/")
async def read_root():
    return {"message": "Drawing Game Signaling Server"}

def start_server():
    import uvicorn
    uvicorn.run(
        "server:app", 
        host="0.0.0.0", 
        port=8000, 
        ssl_keyfile="certs/key.pem", 
        ssl_certfile="certs/cert.pem",      
        reload=True,
        log_level="debug"
    )

if __name__ == "__main__":
    start_server()