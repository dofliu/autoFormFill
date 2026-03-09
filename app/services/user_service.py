from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_profile import UserProfile
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate


async def create_user(db: AsyncSession, data: UserProfileCreate) -> UserProfile:
    user = UserProfile(**data.model_dump())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user(db: AsyncSession, user_id: int) -> UserProfile | None:
    result = await db.execute(select(UserProfile).where(UserProfile.id == user_id))
    return result.scalar_one_or_none()


async def list_users(db: AsyncSession) -> list[UserProfile]:
    result = await db.execute(select(UserProfile))
    return list(result.scalars().all())


async def update_user(
    db: AsyncSession, user_id: int, data: UserProfileUpdate
) -> UserProfile | None:
    user = await get_user(db, user_id)
    if not user:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    user = await get_user(db, user_id)
    if not user:
        return False
    await db.delete(user)
    await db.commit()
    return True
