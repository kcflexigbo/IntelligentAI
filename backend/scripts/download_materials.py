"""
Utilities for downloading Introduction to Computer Science course materials.
"""
import asyncio
import os
import requests
from pathlib import Path
from typing import List
from urllib.parse import urlparse


async def download_file(url: str, destination: Path) -> Path:
    """Download a file from URL to destination."""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    with open(destination, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return destination


async def download_from_github_repo(repo_url: str, destination_dir: Path, extensions: List[str] = None) -> List[Path]:
    """
    Download files from a GitHub repository.
    Note: This is a simplified version. For full functionality, use GitHub API.
    """
    if extensions is None:
        extensions = ['.pdf', '.md', '.txt']
    
    # For now, return empty list - actual implementation would use GitHub API
    # or web scraping to find and download files
    print(f"GitHub download not fully implemented for {repo_url}")
    return []


async def download_cs_materials(destination_dir: Path) -> List[Path]:
    """
    Download Introduction to Computer Science materials from various sources.
    
    Returns:
        List of Path objects to downloaded files
    """
    downloaded_files = []
    destination_dir = Path(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    
    # Example sources for CS materials:
    # 1. MIT OpenCourseWare - Introduction to Computer Science and Programming in Python
    # 2. OpenStax Computer Science textbook
    # 3. Various GitHub repositories with CS notes
    
    sources = [
        # Add URLs here when available
        # Example:
        # {
        #     "url": "https://example.com/cs-textbook.pdf",
        #     "filename": "cs-textbook.pdf"
        # }
        {
            "url": "https://assets.openstax.org/oscms-prodcms/media/documents/Introduction_To_Computer_Science_-_WEB.pdf",
            "filename": "Introduction_To_Computer_Science_-_WEB.pdf"
        }
    ]
    
    print("Note: Add actual download URLs to sources list in download_materials.py")
    print("For now, you can manually place course material files in a directory")
    print(f"and the script will process files from: {destination_dir}")
    
    # Check if files already exist in destination directory
    existing_files = list(destination_dir.glob("*"))
    existing_files = [f for f in existing_files if f.is_file()]
    
    if existing_files:
        print(f"Found {len(existing_files)} existing files in {destination_dir}")
        downloaded_files.extend(existing_files)
    
    # Download from sources
    for source in sources:
        try:
            url = source["url"]
            filename = source.get("filename", os.path.basename(urlparse(url).path))
            dest_path = destination_dir / filename
            
            print(f"Downloading {filename}...")
            await download_file(url, dest_path)
            downloaded_files.append(dest_path)
            
        except Exception as e:
            print(f"Error downloading {source.get('url', 'unknown')}: {e}")
    
    return downloaded_files


