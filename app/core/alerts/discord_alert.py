import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone

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


def send_discord_dev_alert(
    *,
    webhook_url: str,
    service_url: str,
    metric_name: str,
    current_value: float,
    threshold_value: float,
    context: Dict[str, Any],
    stats: Dict[str, Any],
    action: str,
    dedup_key: Optional[str] = None,
    username: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> Dict[str, Any]:
    """개발자 친화적 한국어 Discord 임베드 전송.

    Parameters
    ----------
    webhook_url: Discord Webhook URL (필수)
    service_url: 저장소 또는 서비스 식별 URL (예: https://github.com/org/repo)
    metric_name: 지표명 (예: cpu, memory)
    current_value: 현재(예측) 값
    threshold_value: 임계값(z-threshold 등)
    context: 런타임/시간대/예상 사용자 등 컨텍스트 dict
    stats: 평균/표준편차/최대값/점수 등 통계 dict
    action: 권고 조치 메시지 (한국어)
    dedup_key: 중복 방지 식별자 (footer 표기용)
    username, avatar_url: Discord 표시 이름 / 아바타
    """
    if not webhook_url:
        print("[디스코드] 웹훅 미설정, 개발자용 임베드 전송 대신 출력")
        return {"sent": False, "reason": "no webhook"}

    # 색상: 경고 빨강
    color_red = 0xE53935

    # 지표명 한국어 매핑
    metric_kr = {
        "total_events": "총 이벤트 수",
        "avg_cpu": "평균 CPU 사용률",
        "avg_memory": "평균 메모리 사용률",
        "unique_machines": "활성 머신 수",
    }.get(metric_name, metric_name)

    # 임베드 필드 구성 (개발자 친화적 한국어)
    fields_list = [
        {"name": "저장소", "value": f"[{service_url.split('/')[-1]}]({service_url})", "inline": False},
        {"name": "지표", "value": metric_kr, "inline": True},
        {"name": "이상 점수 vs 임계값", "value": f"**{current_value:.2f}** / {threshold_value:.2f}", "inline": True},
    ]

    # 컨텍스트 - 개발자 친화적 포맷
    if context:
        ctx_parts = []
        
        # 환경
        runtime = context.get("runtime_env")
        if runtime:
            env_text = "프로덕션" if runtime == "prod" else "개발"
            ctx_parts.append(f"**환경**: {env_text}")
        
        # 시간대
        slot = context.get("time_slot")
        if slot:
            slot_text = {"peak": "피크타임", "normal": "일반", "low": "한가한", "weekend": "주말"}.get(slot, slot)
            ctx_parts.append(f"**시간대**: {slot_text}")
        
        # 사용자 수
        users = context.get("expected_users")
        if users:
            ctx_parts.append(f"**예상 사용자**: {users:,}명")
        
        # 서비스 타입
        svc = context.get("service_type")
        if svc:
            svc_text = {"web": "웹 서비스", "api": "API 서버", "db": "데이터베이스"}.get(svc, svc)
            ctx_parts.append(f"**타입**: {svc_text}")
        
        # 모델 버전
        model = context.get("model_version")
        if model:
            ctx_parts.append(f"**모델**: {model}")
        
        if ctx_parts:
            fields_list.append({
                "name": "실행 컨텍스트",
                "value": "\n".join(ctx_parts),
                "inline": False,
            })

    # 통계 - 개발자가 이해하기 쉽게
    if stats:
        stat_parts = []
        
        # 예측 vs 과거
        max_pred = stats.get("max_pred")
        hist_mean = stats.get("hist_mean")
        if max_pred is not None and hist_mean is not None:
            increase_pct = ((max_pred - hist_mean) / hist_mean * 100) if hist_mean > 0 else 0
            stat_parts.append(f"**예측 최대값**: {max_pred:.2f} (평균 대비 +{increase_pct:.0f}%)")
        
        # 평균 예측
        avg_pred = stats.get("avg_pred")
        if avg_pred is not None:
            stat_parts.append(f"**예측 평균**: {avg_pred:.2f}")
        
        # 과거 통계
        if hist_mean is not None:
            hist_std = stats.get("hist_std", 0)
            stat_parts.append(f"**과거 평균**: {hist_mean:.2f} (표준편차: {hist_std:.2f})")
        
        # 중앙값
        hist_median = stats.get("hist_median")
        if hist_median is not None:
            stat_parts.append(f"**과거 중앙값**: {hist_median:.2f}")
        
        # 세부 점수
        score_bd = stats.get("score_breakdown")
        if isinstance(score_bd, dict):
            bd_parts = []
            bd_labels = {
                "avg_based": "평균 기반",
                "max_based": "최대값 기반",
                "change_rate": "변화율"
            }
            for key, val in score_bd.items():
                label = bd_labels.get(key, key)
                try:
                    bd_parts.append(f"{label}: {float(val):.2f}")
                except Exception:
                    bd_parts.append(f"{label}: {val}")
            if bd_parts:
                stat_parts.append(f"**세부 분석**: {', '.join(bd_parts)}")
        
        if stat_parts:
            fields_list.append({
                "name": "통계 분석",
                "value": "\n".join(stat_parts),
                "inline": False,
            })

    # 권고 조치 - 눈에 띄게
    if action:
        fields_list.append({
            "name": "권장 조치",
            "value": f"```\n{action}\n```",
            "inline": False,
        })

    embed = {
        "title": "MCP 이상 탐지 경고",
        "description": f"**{metric_kr}** 지표에서 이상 패턴이 감지되었습니다.\n즉시 확인이 필요합니다.",
        "url": service_url,
        "color": color_red,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": fields_list,
    }

    if dedup_key:
        embed["footer"] = {"text": dedup_key}

    payload: Dict[str, Any] = {"embeds": [embed]}

    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url

    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(webhook_url, data=json.dumps(payload), headers=headers, timeout=5)
        return {"sent": resp.ok, "status_code": resp.status_code, "text": resp.text}
    except Exception as exc:
        print(f"[디스코드] 전송 실패: {exc}")
        return {"sent": False, "reason": str(exc)}
