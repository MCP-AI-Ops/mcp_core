from fastapi import APIRouter, HTTPException
from app.schemas.predict import PredictRequest, PredictResponse
from app.services.model_runner import estimate

router = APIRouter()

@router.post("", response_model=PredictResponse)
async def predict(req: PredictRequest):
    try:
        return await estimate(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
