import os
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
SYNC_ENDPOINT = f"{BACKEND_URL}/api/v1/chat/sync"
TIMEOUT = 90.0


def call_backend_sync(message: str, thread_id: str) -> dict:
    try:
        res = httpx.post(
            SYNC_ENDPOINT,
            json={"message": message, "thread_id": thread_id},
            timeout=TIMEOUT,
        )
        res.raise_for_status()
        return res.json()
    except httpx.TimeoutException:
        raise TimeoutError
    except httpx.ConnectError:
        raise ConnectionError
