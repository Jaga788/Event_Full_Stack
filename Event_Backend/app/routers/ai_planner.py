from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.core.security import require_roles
from app.database import get_db
from app.models.user import User
from app.schemas.ai_planner import EventPlanRead, EventPlanRequest
from app.services import ai_planner_service
from app.services.ai_planner_service import (
    InvalidEventCategoryError,
    PlannerNotConfiguredError,
    PlannerProviderError,
)

router = APIRouter(prefix="/ai", tags=["AI event planner"])


@router.post("/event-plan", response_model=EventPlanRead)
async def create_event_plan(
    request: EventPlanRequest,
    db: Session = Depends(get_db),
    _customer: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> EventPlanRead:
    try:
        return await ai_planner_service.create_event_plan(db, request)
    except InvalidEventCategoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except PlannerNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI planning is not configured. Set OPENAI_API_KEY in the backend environment.",
        ) from exc
    except PlannerProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.detail,
        ) from exc
