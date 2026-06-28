from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.animals.models import AnimalStatus, AnimalType, Gender
from app.animals.repository import AnimalRepository
from app.animals.schemas import (
    AnimalCreate,
    AnimalListParams,
    AnimalListResponse,
    AnimalRead,
    AnimalUpdate,
)
from app.animals.service import AnimalService
from app.database import get_session

router = APIRouter(prefix="/api/animals", tags=["animals"])


def get_animal_service(session: Session = Depends(get_session)) -> AnimalService:
    return AnimalService(AnimalRepository(session))


@router.post("/", response_model=AnimalRead, status_code=status.HTTP_201_CREATED)
def create_animal(
    payload: AnimalCreate,
    service: AnimalService = Depends(get_animal_service),
) -> AnimalRead:
    animal = service.create(payload)
    return AnimalRead.model_validate(animal)


@router.get("/", response_model=AnimalListResponse)
def list_animals(
    type: AnimalType | None = None,
    search: str | None = None,
    breed: str | None = None,
    gender: Gender | None = None,
    status: AnimalStatus | None = None,
    born_after: date | None = None,
    born_before: date | None = None,
    sort_by: str = Query("created_at", pattern="^(tag|breed|date_of_birth|status|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AnimalService = Depends(get_animal_service),
) -> AnimalListResponse:
    params = AnimalListParams(
        type=type,
        search=search,
        breed=breed,
        gender=gender,
        status=status,
        born_after=born_after,
        born_before=born_before,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    items, total = service.list(params)
    return AnimalListResponse(
        items=[AnimalRead.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{animal_id}", response_model=AnimalRead)
def get_animal(
    animal_id: UUID,
    service: AnimalService = Depends(get_animal_service),
) -> AnimalRead:
    return AnimalRead.model_validate(service.get(animal_id))


@router.patch("/{animal_id}", response_model=AnimalRead)
def update_animal(
    animal_id: UUID,
    payload: AnimalUpdate,
    service: AnimalService = Depends(get_animal_service),
) -> AnimalRead:
    return AnimalRead.model_validate(service.update(animal_id, payload))


@router.delete("/{animal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_animal(
    animal_id: UUID,
    service: AnimalService = Depends(get_animal_service),
) -> None:
    service.delete(animal_id)
