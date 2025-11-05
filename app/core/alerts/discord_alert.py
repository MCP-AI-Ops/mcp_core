import json
from typing import Optional, Dict, Any

import requests


def send_discord_alert(
    webhook_url: str,
    title: str,
    description: str,
    fields: Optional[Dict[str, Any]] = None,
    *,
    username: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Discord 웹훅 임베드를 전송한다."""
    if not webhook_url:
        print(f"[디스코드] 웹훅 미설정, 전송 대신 출력: {title} / {description}")
        return {"sent": False, "reason": "no webhook"}

    payload: Dict[str, Any] = {
        "embeds": [
            {
                "title": title,
                "description": description,
                "fields": [],
            }
        ]
    }

    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url

    if fields:
        for key, value in fields.items():
            payload["embeds"][0]["fields"].append(
                {"name": str(key), "value": str(value), "inline": False}
            )

    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(webhook_url, data=json.dumps(payload), headers=headers, timeout=5)
        return {"sent": resp.ok, "status_code": resp.status_code, "text": resp.text}
    except Exception as exc:
        print(f"[디스코드] 전송 실패: {exc}")
        return {"sent": False, "reason": str(exc)}
