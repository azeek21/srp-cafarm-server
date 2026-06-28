from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.analytics.schemas import AnalyticsSummary
from app.analytics.service import AnalyticsService
from app.animals.models import AnimalType
from app.animals.repository import AnimalRepository
from app.database import get_session

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def get_analytics_service(session: Session = Depends(get_session)) -> AnalyticsService:
    return AnalyticsService(AnimalRepository(session))


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(
    type: AnimalType | None = None,
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsSummary:
    return service.summary(type)
