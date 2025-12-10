"""
Script to seed Introduction to Computer Science course materials.
Downloads materials from various sources and processes them.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.session import Base
from app.db import models
from app.core.config import settings
from app.services import course_service, s3_service, rag_service
from scripts.download_materials import download_cs_materials


async def seed_course_materials(db: AsyncSession):
    """
    Seed the database with Introduction to Computer Science course materials.
    """
    print("Starting course material seeding...")
    
    # Wait for MinIO to be ready
    print("Checking MinIO/S3 availability...")
    try:
        await s3_service.ensure_bucket_exists()
        print("MinIO/S3 is ready!")
    except Exception as e:
        print(f"Warning: MinIO/S3 not available: {e}")
        print("Skipping file uploads, but course record will be created...")
    
    # 1. Create or get the course
    course = await course_service.get_or_create_course(
        db=db,
        name="Introduction to Computer Science",
        description="Fundamental concepts in computer science including programming, algorithms, and data structures."
    )
    print(f"Course created/found: {course.name} (ID: {course.id})")
    
    # 2. Check if course materials already exist
    from sqlalchemy import select
    existing_docs = await db.execute(
        select(models.Document).where(
            models.Document.course_id == course.id,
            models.Document.is_course_material == True
        )
    )
    existing_count = len(existing_docs.scalars().all())
    
    if existing_count > 0:
        print(f"Course materials already exist ({existing_count} documents). Skipping download and seeding.")
        return
    
    # 3. Download course materials
    print("Downloading course materials...")
    materials_dir = Path("/tmp/cs_materials")
    materials_dir.mkdir(exist_ok=True, parents=True)
    
    downloaded_files = await download_cs_materials(materials_dir)
    print(f"Downloaded/found {len(downloaded_files)} files")
    
    if not downloaded_files:
        print("No files to process. Exiting.")
        return
    
    # 4. Process each file
    for file_path in downloaded_files:
        try:
            filename = file_path.name
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Generate S3 key
            import uuid
            file_ext = file_path.suffix
            s3_key = f"courses/{course.id}/materials/{uuid.uuid4()}{file_ext}"
            
            # Upload to S3
            print(f"Uploading {filename} to S3...")
            try:
                await s3_service.upload_file(file_content, s3_key)
            except Exception as e:
                print(f"Warning: Failed to upload {filename} to S3: {e}")
                print("Continuing without S3 storage...")
                s3_key = None  # Don't fail if S3 is unavailable
            
            # Determine file type
            from app.api.endpoints.documents import detect_file_type
            file_type = detect_file_type(filename)
            
            # Create document record (s3_key may be None if upload failed)
            document = models.Document(
                filename=filename,
                user_id=None,  # Course materials don't belong to a user
                file_type=file_type,
                s3_key=s3_key,  # May be None if S3 unavailable
                is_course_material=True,
                course_id=course.id
            )
            db.add(document)
            await db.commit()
            await db.refresh(document)
            
            # Process and embed
            print(f"Processing {filename}...")
            if file_type == models.FileType.TEXT:
                await rag_service.process_and_embed_document(
                    db=db,
                    document_record=document,
                    file_content=file_content,
                    filename=filename
                )
            else:
                # For images/videos, we would need OCR/transcription here
                # For now, skip non-text files or process them if needed
                print(f"Skipping {filename} - non-text file processing not implemented in seed script")
            
            print(f"✓ Processed {filename}")
            
        except Exception as e:
            print(f"✗ Error processing {file_path}: {e}")
            continue
    
    print("Course material seeding completed!")


async def main():
    """Main function to run the seeding script."""
    try:
        # Create database connection
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
        
        async with async_session_maker() as db:
            try:
                await seed_course_materials(db)
                print("Course material seeding completed successfully!")
            except Exception as e:
                print(f"Error during seeding: {e}")
                import traceback
                traceback.print_exc()
            finally:
                await engine.dispose()
    except Exception as e:
        print(f"Failed to connect to database or run seeding: {e}")
        import traceback
        traceback.print_exc()
        # Don't exit with error code - allow container to continue
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

