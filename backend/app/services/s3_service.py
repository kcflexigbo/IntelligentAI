"""
S3/MinIO service for file storage operations.
"""
import io
from typing import Optional
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from app.core.config import settings

# Initialize S3 client
s3_client = boto3.client(
    's3',
    endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
    aws_access_key_id=settings.MINIO_ACCESS_KEY,
    aws_secret_access_key=settings.MINIO_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)


async def ensure_bucket_exists():
    """Ensure the bucket exists, create if it doesn't."""
    try:
        s3_client.head_bucket(Bucket=settings.MINIO_BUCKET_NAME)
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == '404':
            # Bucket doesn't exist, create it
            s3_client.create_bucket(Bucket=settings.MINIO_BUCKET_NAME)
            print(f"Created bucket: {settings.MINIO_BUCKET_NAME}")
        else:
            raise


async def upload_file(file_content: bytes, s3_key: str, content_type: Optional[str] = None) -> str:
    """
    Upload a file to MinIO/S3.
    
    Args:
        file_content: The file content as bytes
        s3_key: The S3 key (path) where the file should be stored
        content_type: Optional MIME type of the file
        
    Returns:
        The S3 key where the file was stored
    """
    await ensure_bucket_exists()
    
    extra_args = {}
    if content_type:
        extra_args['ContentType'] = content_type
    
    s3_client.put_object(
        Bucket=settings.MINIO_BUCKET_NAME,
        Key=s3_key,
        Body=file_content,
        **extra_args
    )
    
    return s3_key


async def download_file(s3_key: str) -> bytes:
    """
    Download a file from MinIO/S3.
    
    Args:
        s3_key: The S3 key (path) of the file to download
        
    Returns:
        The file content as bytes
    """
    try:
        response = s3_client.get_object(
            Bucket=settings.MINIO_BUCKET_NAME,
            Key=s3_key
        )
        return response['Body'].read()
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise FileNotFoundError(f"File not found: {s3_key}")
        raise


async def delete_file(s3_key: str) -> bool:
    """
    Delete a file from MinIO/S3.
    
    Args:
        s3_key: The S3 key (path) of the file to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        s3_client.delete_object(
            Bucket=settings.MINIO_BUCKET_NAME,
            Key=s3_key
        )
        return True
    except ClientError:
        return False


async def get_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    """
    Generate a presigned URL for accessing a file (GET).
    Uses external endpoint so frontend can access it.
    
    Args:
        s3_key: The S3 key (path) of the file
        expires_in: Expiration time in seconds (default: 1 hour)
        
    Returns:
        A presigned URL string with external endpoint
    """
    try:
        # Create a temporary client with external endpoint for presigned URLs
        external_client = boto3.client(
            's3',
            endpoint_url=f"http://{settings.MINIO_EXTERNAL_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        
        url = external_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.MINIO_BUCKET_NAME,
                'Key': s3_key
            },
            ExpiresIn=expires_in
        )
        return url
    except ClientError as e:
        raise Exception(f"Failed to generate presigned URL: {str(e)}")


async def get_presigned_upload_url(s3_key: str, content_type: Optional[str] = None, expires_in: int = 3600) -> str:
    """
    Generate a presigned URL for uploading a file (PUT).
    Uses external endpoint so frontend can upload directly.
    
    Args:
        s3_key: The S3 key (path) where the file will be stored
        content_type: Optional MIME type of the file
        expires_in: Expiration time in seconds (default: 1 hour)
        
    Returns:
        A presigned URL string for uploading with external endpoint
    """
    try:
        await ensure_bucket_exists()
        
        # Create a temporary client with external endpoint for presigned URLs
        external_client = boto3.client(
            's3',
            endpoint_url=f"http://{settings.MINIO_EXTERNAL_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        
        params = {
            'Bucket': settings.MINIO_BUCKET_NAME,
            'Key': s3_key
        }
        
        # Add ContentType if provided
        if content_type:
            params['ContentType'] = content_type
        
        url = external_client.generate_presigned_url(
            'put_object',
            Params=params,
            ExpiresIn=expires_in,
            HttpMethod='PUT'
        )
        return url
    except ClientError as e:
        raise Exception(f"Failed to generate presigned upload URL: {str(e)}")


async def file_exists(s3_key: str) -> bool:
    """
    Check if a file exists in MinIO/S3.
    
    Args:
        s3_key: The S3 key (path) to check
        
    Returns:
        True if file exists, False otherwise
    """
    try:
        s3_client.head_object(
            Bucket=settings.MINIO_BUCKET_NAME,
            Key=s3_key
        )
        return True
    except ClientError:
        return False

