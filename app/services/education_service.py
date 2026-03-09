from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.education_experience import EducationExperience
from app.schemas.education_experience import (
    EducationExperienceCreate,
    EducationExperienceUpdate,
)


async def create_entry(
    db: AsyncSession, user_id: int, data: EducationExperienceCreate
) -> EducationExperience:
    entry = EducationExperience(user_id=user_id, **data.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def get_entry(
    db: AsyncSession, user_id: int, entry_id: int
) -> EducationExperience | None:
    result = await db.execute(
        select(EducationExperience).where(
            EducationExperience.id == entry_id,
            EducationExperience.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_entries(
    db: AsyncSession, user_id: int
) -> list[EducationExperience]:
    result = await db.execute(
        select(EducationExperience).where(
            EducationExperience.user_id == user_id
        )
    )
    return list(result.scalars().all())


async def update_entry(
    db: AsyncSession, user_id: int, entry_id: int, data: EducationExperienceUpdate
) -> EducationExperience | None:
    entry = await get_entry(db, user_id, entry_id)
    if not entry:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(entry, key, value)
    await db.commit()
    await db.refresh(entry)
    return entry


async def delete_entry(db: AsyncSession, user_id: int, entry_id: int) -> bool:
    entry = await get_entry(db, user_id, entry_id)
    if not entry:
        return False
    await db.delete(entry)
    await db.commit()
    return True
