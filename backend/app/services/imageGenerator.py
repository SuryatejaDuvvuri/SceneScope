import os
import time
import uuid
from typing import Optional

import requests

from app.config import settings
from app.services.textSummary import summarize_to_chars


class ImageResult:
    def __init__(self, filePath: str, source: str):
        self.filePath = filePath
        self.source = source

    def __repr__(self):
        return f"ImageResult(filePath={self.filePath!r}, source={self.source!r})"


STABILITY_MAX_PROMPT_LENGTH = 1900  # Leave headroom under common 2k-char prompt limits.

NEGATIVE_PROMPT = (
    "photorealistic, photography, photo, realistic render, glossy render, 3d render, CGI, "
    "hyper-detailed texture, subsurface scattering, ray tracing, physically based rendering, "
    "neon colors, black and white, monochrome, greyscale, "
    "empty room, no people, unpopulated scene"
)


def truncatePrompt(prompt: str, maxLength: int = STABILITY_MAX_PROMPT_LENGTH) -> str:
    """Summarize a prompt to fit within API limits while keeping salient details."""
    if len(prompt) <= maxLength:
        return prompt
    summarized = summarize_to_chars(
        prompt,
        maxLength,
        focus_text="scene visual composition lighting camera mood",
    )
    print(f"Prompt summarized from {len(prompt)} to {len(summarized)} chars")
    return summarized


def saveImage(imageData: bytes, directory: str) -> str:
    os.makedirs(directory, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    filePath = os.path.join(directory, filename)
    with open(filePath, "wb") as f:
        f.write(imageData)
    return filePath


def _prepare_prompt(prompt: str) -> str:
    """Truncate the prompt if needed. Style is already set by promptBuilder."""
    return truncatePrompt(prompt)


def _poll_replicate_prediction(prediction_url: str, headers: dict) -> str:
    for _ in range(30):
        poll = requests.get(prediction_url, headers=headers, timeout=30)
        poll_data = poll.json()
        status = poll_data.get("status")

        if status == "succeeded" and poll_data.get("output"):
            output = poll_data["output"]
            return output[0] if isinstance(output, list) else output
        if status in ("failed", "canceled"):
            raise RuntimeError(f"Replicate prediction failed: {poll_data}")

        time.sleep(3)

    raise RuntimeError("Replicate prediction timed out.")


def _replicate_predict(input_payload: dict) -> str:
    url = "https://api.replicate.com/v1/predictions"
    headers = {
        "Authorization": f"Token {settings.REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    model_version = (settings.REPLICATE_MODEL_VERSION or "").strip()
    if not model_version:
        raise RuntimeError(
            "Replicate model version not configured. Set REPLICATE_MODEL_VERSION in backend/.env."
        )

    payload = {
        "version": model_version,
        "input": input_payload,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=90)
    data = response.json()

    if response.status_code == 401:
        raise RuntimeError(
            "Replicate authentication failed (401). Check REPLICATE_API_TOKEN in backend/.env."
        )
    if response.status_code >= 400:
        raise RuntimeError(f"Replicate API HTTP {response.status_code}: {data}")

    if "error" in data:
        raise RuntimeError(f"Replicate API error: {data['error']}")
    if "urls" not in data or "get" not in data["urls"]:
        raise RuntimeError(f"Replicate: no prediction URL in response: {data}")

    return _poll_replicate_prediction(data["urls"]["get"], headers)


def generateImageReplicate(prompt: str, reference_image_url: str | None = None) -> Optional[ImageResult]:
    if not settings.REPLICATE_API_TOKEN:
        raise RuntimeError("Replicate API token not configured")

    final_prompt = _prepare_prompt(prompt)

    base_input = {
        "prompt": final_prompt,
        "negative_prompt": NEGATIVE_PROMPT,
        "width": 1024,
        "height": 576,
    }

    image_url: str
    if reference_image_url:
        # Try image-conditioned generation first when a public reference image URL is available.
        # Not all model versions accept `image`/`prompt_strength`; if unsupported, fallback to text-only.
        # prompt_strength 0.35 keeps ~65% of the reference image for visual consistency during refinement.
        conditioned_input = {
            **base_input,
            "image": reference_image_url,
            "prompt_strength": 0.35,
        }
        try:
            image_url = _replicate_predict(conditioned_input)
        except Exception as e:
            print(f"Replicate image-conditioning unsupported or failed; fallback to text-only: {e}")
            image_url = _replicate_predict(base_input)
    else:
        image_url = _replicate_predict(base_input)

    img_response = requests.get(image_url, timeout=30)
    img_response.raise_for_status()
    filePath = saveImage(img_response.content, settings.STATIC_DIR)
    return ImageResult(filePath=filePath, source="replicate")


def generateImageStability(prompt: str) -> Optional[ImageResult]:
    if not settings.STABILITY_API_KEY:
        raise RuntimeError("Stability API key not configured")

    final_prompt = _prepare_prompt(prompt)

    url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    headers = {
        "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
        "Accept": "image/*",
    }
    payload = {
        "prompt": final_prompt,
        "negative_prompt": NEGATIVE_PROMPT,
        "output_format": "png",
        "aspect_ratio": "16:9",
    }

    # Stability Core expects multipart/form-data payloads.
    response = requests.post(
        url,
        headers=headers,
        data=payload,
        files={"none": ("", "")},
        timeout=90,
    )

    if response.status_code == 401:
        raise RuntimeError(
            "Stability authentication failed (401). Check STABILITY_API_KEY in backend/.env."
        )
    if response.status_code >= 400:
        try:
            error_data = response.json()
        except Exception:
            error_data = response.text
        raise RuntimeError(f"Stability API HTTP {response.status_code}: {error_data}")

    filePath = saveImage(response.content, settings.STATIC_DIR)
    return ImageResult(filePath=filePath, source="stability")


def _get_provider_order() -> list[str]:
    configured = [provider.strip().lower() for provider in settings.IMAGE_PROVIDER_ORDER.split(",") if provider.strip()]
    valid = [provider for provider in configured if provider in {"stability", "replicate"}]
    return valid or ["stability", "replicate"]


def generateImage(prompt: str, reference_image_url: str | None = None) -> ImageResult:
    """Generate an image, optionally conditioning on a previous image URL for refinement."""
    errors: list[str] = []

    # When refining with a reference image, prioritize Replicate (supports img2img).
    # Stability's core endpoint is text-only and would ignore the reference entirely.
    if reference_image_url:
        providers = [p for p in _get_provider_order() if p == "replicate"]
        if not providers:
            providers = ["replicate"]
        # Keep other providers as text-only fallback
        providers += [p for p in _get_provider_order() if p not in providers]
    else:
        providers = _get_provider_order()

    for provider in providers:
        try:
            if provider == "stability":
                result = generateImageStability(prompt)
            else:
                result = generateImageReplicate(prompt, reference_image_url=reference_image_url)

            if result:
                return result
        except Exception as e:
            print(f"{provider.title()} failed: {e}")
            errors.append(f"{provider}: {e}")

    raise RuntimeError(
        "All image generators failed. " + " | ".join(errors)
        if errors else
        "All image generators failed. Check API keys/model configuration."
    )
