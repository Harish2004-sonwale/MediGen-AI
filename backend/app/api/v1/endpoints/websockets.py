"""API & WebSocket Routes for Live Telemetry Waveforms, Collaboration and WebRTC Signaling."""

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/telehealth/ice-servers", summary="Get WebRTC STUN/TURN ICE Servers")
def get_ice_servers() -> Dict[str, Any]:
    """Returns standard STUN ICE server configuration for WebRTC signaling."""
    return {
        "iceServers": [
            {"urls": "stun:stun.l.google.com:19302"},
            {"urls": "stun:stun1.l.google.com:19302"},
            {"urls": "stun:stun.cloudflare.com:3478"},
        ]
    }


@router.get("/ws/stats", summary="Get Active WebSocket Stats")
def get_websocket_stats() -> Dict[str, Any]:
    """Returns active WebSocket channel metrics without PHI."""
    return websocket_manager.get_channel_stats()


@router.post("/telemetry/{patient_id}/broadcast", summary="Broadcast Live Vital Waveform Frame")
async def broadcast_patient_telemetry(patient_id: str, frame: Dict[str, Any]) -> Dict[str, Any]:
    """Helper endpoint to inject a vital waveform frame into the patient's live telemetry channel."""
    await websocket_manager.broadcast_telemetry(patient_id, frame)
    return {"status": "broadcast_sent", "patient_id": patient_id}


# WebSocket Handlers
async def handle_telemetry_ws(websocket: WebSocket, patient_id: str, token: Optional[str] = None):
    auth_info = websocket_manager.authenticate_jwt(token)
    if not auth_info:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket_manager.connect_telemetry(websocket, patient_id, auth_info)
    try:
        while True:
            # Client can send heartbeats or command frames
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
    except Exception as exc:
        logger.debug("Telemetry WS error: %s", exc)
        await websocket_manager.disconnect(websocket)


async def handle_collaboration_ws(websocket: WebSocket, patient_id: str, token: Optional[str] = None):
    auth_info = websocket_manager.authenticate_jwt(token)
    if not auth_info:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket_manager.connect_collaboration(websocket, patient_id, auth_info)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                continue
            try:
                msg = json.loads(data)
                # Broadcast cursor / annotation message to other clinicians in the room
                await websocket_manager.broadcast_collaboration(patient_id, msg, sender=websocket)
            except Exception:
                pass
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
    except Exception as exc:
        logger.debug("Collaboration WS error: %s", exc)
        await websocket_manager.disconnect(websocket)


async def handle_telehealth_ws(websocket: WebSocket, session_id: str, token: Optional[str] = None):
    auth_info = websocket_manager.authenticate_jwt(token)
    if not auth_info:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket_manager.connect_telehealth(websocket, session_id, auth_info)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                continue
            try:
                msg = json.loads(data)
                # Forward WebRTC SDP offer, answer, or ICE candidate to other peer
                await websocket_manager.forward_telehealth_signaling(session_id, msg, sender=websocket)
            except Exception:
                pass
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
    except Exception as exc:
        logger.debug("Telehealth WS error: %s", exc)
        await websocket_manager.disconnect(websocket)
