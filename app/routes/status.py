from fastapi import APIRouter
from app.models.status import StatusQuery, StatusResponse

router = APIRouter()

@router.post("", response_model=StatusResponse)
def status(q: StatusQuery):
    # TODO: 실제 모니터링 소스 조회
    return StatusResponse(
        github_url=q.github_url,
        instance_id="vm-123456",
        cpu_usage=0.42,
        mem_usage=0.63,
        is_healthy=True
    )
