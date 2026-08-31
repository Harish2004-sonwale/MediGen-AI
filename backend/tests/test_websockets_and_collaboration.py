"""Unit & Integration Tests for WebSockets, Live Telemetry and WebRTC Signaling."""

import json
from fastapi.testclient import TestClient
import pytest

from app.core.websocket_manager import websocket_manager
from app.main import app

def test_ice_servers_and_websocket_stats(client: TestClient):
    """Verifies REST endpoints for ICE STUN servers and WebSocket statistics."""
    # 1. ICE Servers
    ice_resp = client.get("/api/v1/telehealth/ice-servers")
    assert ice_resp.status_code == 200
    ice_data = ice_resp.json()
    assert "iceServers" in ice_data
    assert len(ice_data["iceServers"]) >= 1
    assert "stun:" in ice_data["iceServers"][0]["urls"]

    # 2. WS Stats
    stats_resp = client.get("/api/v1/ws/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert "active_telemetry_patients" in stats
    assert "active_collaboration_rooms" in stats
    assert "total_connected_clients" in stats


def test_websocket_telemetry_connection_and_heartbeat(client: TestClient):
    """Verifies WebSocket connection to /ws/telemetry/{patient_id} and ping/pong."""
    with client.websocket_connect("/ws/telemetry/PAT-001") as websocket:
        # Send heartbeat ping
        websocket.send_text("ping")
        response = websocket.receive_text()
        assert response == "pong"


def test_websocket_collaboration_connection_and_broadcast(client: TestClient):
    """Verifies multi-clinician room connection to /ws/collaboration/{patient_id}."""
    with client.websocket_connect("/ws/collaboration/PAT-001") as websocket:
        # Receive the USER_JOINED notification frame
        msg = websocket.receive_text()
        data = json.loads(msg)
        assert data["type"] == "USER_JOINED"

        # Send cursor movement action
        cursor_action = {
            "type": "CURSOR_MOVE",
            "user_id": "user-001",
            "x": 250,
            "y": 140,
        }
        websocket.send_text(json.dumps(cursor_action))

        # Ping
        websocket.send_text("ping")
        assert websocket.receive_text() == "pong"


def test_websocket_telehealth_webrtc_signaling(client: TestClient):
    """Verifies WebRTC SDP offer/answer signaling exchange over /ws/telehealth/{session_id}."""
    with client.websocket_connect("/ws/telehealth/SES-ROOM-101") as ws1:
        with client.websocket_connect("/ws/telehealth/SES-ROOM-101") as ws2:
            # ws1 sends SDP offer
            offer_payload = {
                "type": "OFFER",
                "sdp": "v=0\r\no=- 20518 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n",
            }
            ws1.send_text(json.dumps(offer_payload))

            # ws2 receives forwarded offer
            recv_text = ws2.receive_text()
            recv_msg = json.loads(recv_text)
            assert recv_msg["type"] == "OFFER"
            assert "sdp" in recv_msg


def test_telemetry_broadcast_helper(client: TestClient):
    """Verifies POST /api/v1/telemetry/{patient_id}/broadcast helper."""
    resp = client.post(
        "/api/v1/telemetry/PAT-001/broadcast",
        json={"ecg_lead_ii": [0.12, 0.15, 0.85, -0.2, 0.05], "spo2": 98},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "broadcast_sent"
