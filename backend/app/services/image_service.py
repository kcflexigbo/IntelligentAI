"""
Image processing service for OCR text extraction.
"""
import io
from typing import Optional
from PIL import Image
import easyocr

# Initialize EasyOCR reader (lazy initialization on first use)
_ocr_reader = None


def get_ocr_reader():
    """Lazy initialization of OCR reader."""
    global _ocr_reader
    if _ocr_reader is None:
        # Initialize with English language, GPU if available
        _ocr_reader = easyocr.Reader(['en'], gpu=False)
    return _ocr_reader


async def extract_text_from_image(image_content: bytes) -> str:
    """
    Extract text from an image using OCR.
    
    Args:
        image_content: The image file content as bytes
        
    Returns:
        Extracted text as a string
    """
    try:
        # Load image from bytes
        image = Image.open(io.BytesIO(image_content))
        
        # Convert to RGB if necessary (EasyOCR works better with RGB)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert PIL Image to numpy array for EasyOCR
        import numpy as np
        image_array = np.array(image)
        
        # Perform OCR
        reader = get_ocr_reader()
        results = reader.readtext(image_array)
        
        # Extract text from results
        extracted_texts = [result[1] for result in results]  # result[1] is the text
        full_text = '\n'.join(extracted_texts)
        
        return full_text if full_text.strip() else ""
        
    except Exception as e:
        print(f"Error during OCR: {e}")
        return f"[OCR Error: {str(e)}]"


async def extract_text_from_image_path(image_path: str) -> str:
    """
    Extract text from an image file path.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Extracted text as a string
    """
    with open(image_path, 'rb') as f:
        image_content = f.read()
    return await extract_text_from_image(image_content)


