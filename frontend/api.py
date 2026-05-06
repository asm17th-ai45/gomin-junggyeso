import os
from mock import MOCK_SCENARIO_1, MOCK_SCENARIO_2

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
SYNC_ENDPOINT = f"{BACKEND_URL}/api/v1/chat/sync"


def call_backend_sync(message: str, thread_id: str) -> dict:
    """백엔드 호출. 현재는 mock 데이터 반환"""
    if "휴학" in message or "인턴" in message:
        return MOCK_SCENARIO_2
    return MOCK_SCENARIO_1
