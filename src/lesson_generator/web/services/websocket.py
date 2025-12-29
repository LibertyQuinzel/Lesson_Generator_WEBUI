"""
WebSocket connection management for real-time updates.

This module handles WebSocket connections for providing real-time progress
updates during lesson generation.
"""

import json
from typing import Dict, Set
from fastapi import WebSocket


class WebSocketManager:
    """
    Manages WebSocket connections for real-time updates.
    
    This class handles client connections, message broadcasting,
    and connection lifecycle management.
    """
    
    def __init__(self):
        # Active connections by lesson_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, lesson_id: str):
        """Accept a new WebSocket connection for a specific lesson."""
        
        await websocket.accept()
        
        if lesson_id not in self.active_connections:
            self.active_connections[lesson_id] = set()
        
        self.active_connections[lesson_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, lesson_id: str):
        """Remove a WebSocket connection."""
        
        if lesson_id in self.active_connections:
            self.active_connections[lesson_id].discard(websocket)
            
            # Clean up empty sets
            if not self.active_connections[lesson_id]:
                del self.active_connections[lesson_id]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        
        try:
            await websocket.send_text(json.dumps(message))
        except Exception:
            # Connection might be closed
            pass
    
    async def broadcast_to_lesson(self, lesson_id: str, message: dict):
        """Broadcast a message to all connections for a specific lesson."""
        
        if lesson_id not in self.active_connections:
            return
        
        # Copy the set to avoid modification during iteration
        connections = self.active_connections[lesson_id].copy()
        
        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                # Remove failed connections
                self.disconnect(connection, lesson_id)
    
    async def broadcast_progress_update(
        self,
        lesson_id: str,
        progress_percentage: float,
        current_step: str,
        message: str,
    ):
        """Send a progress update to all connections for a lesson."""
        
        update_message = {
            "type": "progress_update",
            "lesson_id": lesson_id,
            "progress_percentage": progress_percentage,
            "current_step": current_step,
            "message": message,
            "timestamp": "2023-12-07T10:30:00Z",  # TODO: Use actual timestamp
        }
        
        await self.broadcast_to_lesson(lesson_id, update_message)
    
    async def broadcast_status_change(
        self,
        lesson_id: str,
        old_status: str,
        new_status: str,
        message: str,
    ):
        """Send a status change notification to all connections for a lesson."""
        
        status_message = {
            "type": "status_change",
            "lesson_id": lesson_id,
            "old_status": old_status,
            "new_status": new_status,
            "message": message,
            "timestamp": "2023-12-07T10:30:00Z",  # TODO: Use actual timestamp
        }
        
        await self.broadcast_to_lesson(lesson_id, status_message)
    
    async def broadcast_completion(
        self,
        lesson_id: str,
        download_url: str,
        result_summary: dict,
    ):
        """Send a completion notification to all connections for a lesson."""
        
        completion_message = {
            "type": "completion",
            "lesson_id": lesson_id,
            "download_url": download_url,
            "result_summary": result_summary,
            "timestamp": "2023-12-07T10:30:00Z",  # TODO: Use actual timestamp
        }
        
        await self.broadcast_to_lesson(lesson_id, completion_message)


# Singleton instance for dependency injection
_websocket_manager_instance = None


def get_websocket_manager() -> WebSocketManager:
    """Get the singleton WebSocketManager instance."""
    global _websocket_manager_instance
    
    if _websocket_manager_instance is None:
        _websocket_manager_instance = WebSocketManager()
    
    return _websocket_manager_instance