from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user_profile import (
    UserProfileCreate,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.services import user_service

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.post("/", response_model=UserProfileResponse, status_code=201)
async def create_user(data: UserProfileCreate, db: AsyncSession = Depends(get_db)):
    return await user_service.create_user(db, data)


@router.get("/", response_model=list[UserProfileResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    return await user_service.list_users(db)


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


@router.put("/{user_id}", response_model=UserProfileResponse)
async def update_user(
    user_id: int, data: UserProfileUpdate, db: AsyncSession = Depends(get_db)
):
    user = await user_service.update_user(db, user_id, data)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await user_service.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
