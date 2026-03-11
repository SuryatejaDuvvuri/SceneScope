import requests
import base64
import os
import uuid
import json
from typing import Optional
from app.config import settings


class ImageResult:
    def __init__(self, filePath: str, source: str):
        self.filePath = filePath
        self.source = source
    def __repr__(self):
        return f"ImageResult(filePath={self.filePath!r}, source={self.source!r})"


STABILITY_MAX_PROMPT_LENGTH = 1900  # Leave headroom under Stability's 2000 char limit


def truncatePrompt(prompt: str, maxLength: int = STABILITY_MAX_PROMPT_LENGTH) -> str:
    """Smartly truncate a prompt to fit within API limits.
    Truncates at the last comma boundary before the limit to avoid cutting mid-phrase."""
    if len(prompt) <= maxLength:
        return prompt
    truncated = prompt[:maxLength]
    # Cut at last comma to avoid mid-phrase truncation
    lastComma = truncated.rfind(",")
    if lastComma > maxLength * 0.5:
        truncated = truncated[:lastComma]
    print(f"⚠️  Prompt truncated from {len(prompt)} to {len(truncated)} chars")
    return truncated


def saveImage(imageData: bytes, directory: str) -> str:
    os.makedirs(directory, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    filePath = os.path.join(directory, filename)
    with open(filePath, "wb") as f:
        f.write(imageData)
    return filePath


def generateImageStability(prompt: str) -> Optional[ImageResult]:
    """Primary: Stability AI (Stable Diffusion XL, sketch style, v1 endpoint)."""
    if not settings.STABILITY_API_KEY:
        raise RuntimeError("Stability API key not configured")

    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    headers = {
        "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    style_suffix = ", pencil sketch, line art, storyboard, black and white, rough hand-drawn look"
    sketch_prompt = truncatePrompt(f"{prompt}{style_suffix}")
    payload = {
        "text_prompts": [{"text": sketch_prompt}],
        "cfg_scale": 7,
        "height": 1024,
        "width": 1024,
        "samples": 1,
        "steps": 30
    }
    response = requests.post(url, headers=headers, json=payload, timeout=90)
    data = response.json()
    if "artifacts" not in data or not data["artifacts"]:
        raise RuntimeError(f"Stability AI: no image data in response: {data}")
    b64 = data["artifacts"][0]["base64"]
    imageBytes = base64.b64decode(b64)
    filePath = saveImage(imageBytes, settings.STATIC_DIR)
    return ImageResult(filePath=filePath, source="stability")
def generateImageFal(prompt: str) -> Optional[ImageResult]:

    url = "https://fal.run/fal-ai/flux/schnell"
    headers = {
        "Authorization": f"Key {settings.FAL_KEY}",
        "Content-Type": "application/json"
    }
    style_suffix = ", pencil sketch, line art, storyboard, black and white, rough hand-drawn look"
    sketch_prompt = truncatePrompt(f"{prompt}{style_suffix}")
    payload = {
        "prompt": sketch_prompt,
        "image_size": "landscape_16_9",
        "num_inference_steps": 4,
        "num_images": 1,
        "enable_safety_checker": False
    }
    response = requests.post(url, headers=headers, json=payload, timeout=90)
    data = response.json()
    if "detail" in data or "error" in data:
        raise RuntimeError(f"fal.ai error: {data.get('detail') or data.get('error')}")
    if "images" not in data:
        raise RuntimeError(f"fal.ai unexpected response: {data}")
    image_url = data["images"][0]["url"]
    img_response = requests.get(image_url, timeout=30)
    img_response.raise_for_status()
    filePath = saveImage(img_response.content, settings.STATIC_DIR)
    return ImageResult(filePath=filePath, source="fal")



# --- Gemini text-bison as placeholder (returns a dummy image) ---
def generateImageGemini(prompt: str) -> Optional[ImageResult]:
    """Fallback: Gemini text-bison (returns a placeholder image)."""
    # Gemini does not support image generation, so return a placeholder
    import io
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (1024, 576), color = (220, 220, 220))
    d = ImageDraw.Draw(img)
    d.text((10,10), "[Gemini: No image API]", fill=(0,0,0))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    filePath = saveImage(buf.getvalue(), settings.STATIC_DIR)
    return ImageResult(filePath=filePath, source="gemini-placeholder")


def generateImage(prompt: str) -> ImageResult:
    # Try Stability AI first
    try:
        result = generateImageStability(prompt)
        if result:
            return result
    except Exception as e:
        print(f"Stability AI failed: {e}")

    # Fallback: Gemini (placeholder)
    try:
        result = generateImageGemini(prompt)
        if result:
            return result
    except Exception as e:
        print(f"Gemini failed: {e}")

    # Fallback: Replicate
    try:
        result = generateImageReplicate(prompt)
        if result:
            return result
    except Exception as e:
        print(f"Replicate failed: {e}")

    raise RuntimeError("All image generators failed. Check API keys and rate limits.")

def generateImageReplicate(prompt: str) -> Optional[ImageResult]:

    if not settings.REPLICATE_API_TOKEN:
        raise RuntimeError("Replicate API token not configured")

    url = "https://api.replicate.com/v1/predictions"
    headers = {
        "Authorization": f"Token {settings.REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    # Use a sketch prompt and a public SDXL model (e.g. tencentarc/sketch-sdxl)
    style_suffix = ", pencil sketch, line art, storyboard, black and white, rough hand-drawn look"
    sketch_prompt = truncatePrompt(f"{prompt}{style_suffix}")
    payload = {
        "version": "db21e45a3b6e0c0e2b6e0c0e2b6e0c0e2b6e0c0e2b6e0c0e2b6e0c0e2b6e0c0e",  # tencentarc/sketch-sdxl
        "input": {"prompt": sketch_prompt, "width": 1024, "height": 576}
    }

    response = requests.post(url, headers=headers, json=payload, timeout=90)
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"Replicate API error: {data['error']}")
    if "urls" not in data or "get" not in data["urls"]:
        raise RuntimeError(f"Replicate: no prediction URL in response: {data}")

    # Poll for completion
    import time
    prediction_url = data["urls"]["get"]
    for _ in range(30):
        poll = requests.get(prediction_url, headers=headers)
        poll_data = poll.json()
        if poll_data.get("status") == "succeeded" and poll_data.get("output"):
            image_url = poll_data["output"][0] if isinstance(poll_data["output"], list) else poll_data["output"]
            img_response = requests.get(image_url, timeout=30)
            img_response.raise_for_status()
            filePath = saveImage(img_response.content, settings.STATIC_DIR)
            return ImageResult(filePath=filePath, source="replicate")
        elif poll_data.get("status") in ("failed", "canceled"):
            raise RuntimeError(f"Replicate prediction failed: {poll_data}")
        time.sleep(3)
    raise RuntimeError("Replicate prediction timed out.")