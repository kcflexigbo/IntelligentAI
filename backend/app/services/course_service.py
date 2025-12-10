"""
Course service for managing courses and course materials.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import models


async def get_or_create_course(db: AsyncSession, name: str, description: str = None) -> models.Course:
    """
    Get an existing course or create a new one.
    
    Args:
        db: Database session
        name: Course name
        description: Optional course description
        
    Returns:
        Course model instance
    """
    result = await db.execute(
        select(models.Course).where(models.Course.name == name)
    )
    course = result.scalar_one_or_none()
    
    if not course:
        course = models.Course(name=name, description=description)
        db.add(course)
        await db.commit()
        await db.refresh(course)
    
    return course


async def get_course_by_name(db: AsyncSession, name: str) -> models.Course | None:
    """Get a course by name."""
    result = await db.execute(
        select(models.Course).where(models.Course.name == name)
    )
    return result.scalar_one_or_none()


