"""
Video processing service for transcription using Whisper.
"""
import io
import tempfile
import os
from typing import Optional
from openai import OpenAI
from app.core.config import settings

# Initialize OpenAI client for Whisper API
openai_client = None


def get_openai_client():
    """Lazy initialization of OpenAI client."""
    global openai_client
    if openai_client is None:
        openai_client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
    return openai_client


async def transcribe_video(video_content: bytes, filename: str) -> str:
    """
    Transcribe audio from a video file using OpenAI Whisper API.
    
    Args:
        video_content: The video file content as bytes
        filename: Original filename (used to determine format)
        
    Returns:
        Transcription text as a string
    """
    try:
        # Save video to temporary file
        temp_file = None
        try:
            # Create temporary file with appropriate extension
            file_ext = os.path.splitext(filename)[1] or '.mp4'
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                tmp.write(video_content)
                temp_file = tmp.name
            
            # Open the file for transcription
            with open(temp_file, 'rb') as audio_file:
                # Use Whisper API for transcription
                client = get_openai_client()
                
                # The Whisper API expects audio files
                # For video files, we can pass them directly as Whisper supports video formats
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"  # Optional: specify language for better accuracy
                )
                
                return transcript.text
                
        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
                
    except Exception as e:
        print(f"Error during video transcription: {e}")
        return f"[Transcription Error: {str(e)}]"


async def transcribe_video_from_path(video_path: str) -> str:
    """
    Transcribe audio from a video file path.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Transcription text as a string
    """
    with open(video_path, 'rb') as f:
        video_content = f.read()
    filename = os.path.basename(video_path)
    return await transcribe_video(video_content, filename)


