from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.education_experience import (
    EducationExperienceCreate,
    EducationExperienceResponse,
    EducationExperienceUpdate,
)
from app.services import education_service

router = APIRouter(prefix="/api/v1/users/{user_id}/education", tags=["Education"])


@router.post("/", response_model=EducationExperienceResponse, status_code=201)
async def create_entry(
    user_id: int,
    data: EducationExperienceCreate,
    db: AsyncSession = Depends(get_db),
):
    return await education_service.create_entry(db, user_id, data)


@router.get("/", response_model=list[EducationExperienceResponse])
async def list_entries(user_id: int, db: AsyncSession = Depends(get_db)):
    return await education_service.list_entries(db, user_id)


@router.get("/{entry_id}", response_model=EducationExperienceResponse)
async def get_entry(
    user_id: int, entry_id: int, db: AsyncSession = Depends(get_db)
):
    entry = await education_service.get_entry(db, user_id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.put("/{entry_id}", response_model=EducationExperienceResponse)
async def update_entry(
    user_id: int,
    entry_id: int,
    data: EducationExperienceUpdate,
    db: AsyncSession = Depends(get_db),
):
    entry = await education_service.update_entry(db, user_id, entry_id, data)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(
    user_id: int, entry_id: int, db: AsyncSession = Depends(get_db)
):
    deleted = await education_service.delete_entry(db, user_id, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found")
