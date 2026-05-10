import os
import json
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
SYNC_ENDPOINT = f"{BACKEND_URL}/api/v1/chat/sync"
STREAM_ENDPOINT = f"{BACKEND_URL}/api/v1/chat"
TIMEOUT = 90.0
STREAM_TIMEOUT = httpx.Timeout(300.0, connect=10.0, read=60.0)


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


def call_backend_stream(message: str, thread_id: str):
    try:
        with httpx.stream(
            "POST",
            STREAM_ENDPOINT,
            json={"message": message, "thread_id": thread_id},
            timeout=STREAM_TIMEOUT,
        ) as res:
            res.raise_for_status()
            event_name = "message"
            data_lines = []

            for line in res.iter_lines():
                if line == "":
                    if data_lines:
                        yield event_name, json.loads("\n".join(data_lines))
                    event_name = "message"
                    data_lines = []
                    continue

                if line.startswith("event:"):
                    event_name = line.removeprefix("event:").strip()
                elif line.startswith("data:"):
                    data_lines.append(line.removeprefix("data:").strip())

            if data_lines:
                yield event_name, json.loads("\n".join(data_lines))
    except httpx.TimeoutException:
        raise TimeoutError
    except httpx.ConnectError:
        raise ConnectionError
