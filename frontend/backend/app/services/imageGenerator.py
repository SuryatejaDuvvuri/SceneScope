import requests
import base64
import os
import uuid
from typing import Optional
from app.config import settings


class ImageResult:
    def __init__(self, filePath: str, source: str):
        self.filePath = filePath
        self.source = source 
    def __repr__(self):
        return f"ImageResult(filePath={self.filePath!r}, source={self.source!r})"


def saveImage(imageData: bytes, directory: str) -> str:
    os.makedirs(directory, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    filePath = os.path.join(directory, filename)
    with open(filePath, "wb") as f:
        f.write(imageData)
    return filePath


def generateImageTogether(prompt: str) -> Optional[ImageResult]:
    url = "https://api.together.xyz/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {settings.TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "black-forest-labs/FLUX.1-schnell-Free",
        "prompt": prompt,
        "width": 1024,
        "height": 768,
        "n": 1,
        "response_format": "b64_json"
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    data = response.json()

    b64 = data["data"][0]["b64_json"]
    imageBytes = base64.b64decode(b64)
    filePath = saveImage(imageBytes, settings.STATIC_DIR)
    return ImageResult(filePath=filePath, source="together")


def generateImageOpenAI(prompt: str) -> Optional[ImageResult]:
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "size": "1792x1024",
        "n": 1,
        "response_format": "b64_json"
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    data = response.json()

    b64 = data["data"][0]["b64_json"]
    imageBytes = base64.b64decode(b64)
    filePath = saveImage(imageBytes, settings.STATIC_DIR)
    return ImageResult(filePath=filePath, source="openai")


def generateImage(prompt: str) -> ImageResult:
    result = generateImageTogether(prompt)
    if result:
        return result

    result = generateImageOpenAI(prompt)
    if result:
        return result
