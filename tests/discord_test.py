import os
from app.core.alerts.discord_alert import send_discord_alert

webhook = os.getenv("DISCORD_WEBHOOK_URL")
print("웹훅 설정 여부:", bool(webhook))
res = send_discord_alert(
    webhook,
    "MCP 테스트 알림",
    "MCP 서비스에서 전송한 자동 테스트 알림",
    {"note": "통합 테스트"},
)
print("전송 결과:", res)
