import os
import time
import uuid
from typing import Optional

import requests

from app.config import settings
from app.services.textSummary import summarize_to_chars
from app.services.promptBuilder import buildCharacterPortraitPrompt


class ImageResult:
    def __init__(self, filePath: str, source: str):
        self.filePath = filePath
        self.source = source

    def __repr__(self):
        return f"ImageResult(filePath={self.filePath!r}, source={self.source!r})"


STABILITY_MAX_PROMPT_LENGTH = 1900  # Leave headroom under common 2k-char prompt limits.

NEGATIVE_PROMPT = (
    "photorealistic, photography, photo, DSLR, film still, documentary, magazine cover, "
    "realistic render, glossy render, 3d render, CGI, uncanny valley, hyperreal skin, skin pores, "
    "hyper-detailed texture, subsurface scattering, ray tracing, physically based rendering, "
    "celebrity likeness, recognizable public figure, face swap, "
    "duplicate same person, cloned character, repeated identical face, twin leads, "
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


def generateImageReplicate(
    prompt: str,
    reference_image_url: str | None = None,
    seed: Optional[int] = None,
    width: int = 1024,
    height: int = 576,
) -> Optional[ImageResult]:
    if not settings.REPLICATE_API_TOKEN:
        raise RuntimeError("Replicate API token not configured")

    final_prompt = _prepare_prompt(prompt)

    base_input: dict = {
        "prompt": final_prompt,
        "negative_prompt": NEGATIVE_PROMPT,
        "width": width,
        "height": height,
    }
    if seed is not None:
        base_input["seed"] = seed

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


def generateImageStability(
    prompt: str,
    seed: Optional[int] = None,
    aspect_ratio: str = "16:9",
) -> Optional[ImageResult]:
    if not settings.STABILITY_API_KEY:
        raise RuntimeError("Stability API key not configured")

    final_prompt = _prepare_prompt(prompt)

    url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    headers = {
        "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
        "Accept": "image/*",
    }
    payload: dict = {
        "prompt": final_prompt,
        "negative_prompt": NEGATIVE_PROMPT,
        "output_format": "png",
        "aspect_ratio": aspect_ratio,
    }
    if seed is not None:
        payload["seed"] = str(seed)  # Stability multipart wants strings

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


def generateImageFal(
    prompt: str,
    reference_image_url: str | None = None,
    character_ref_image_url: str | None = None,
    seed: Optional[int] = None,
    width: int = 1024,
    height: int = 576,
) -> Optional[ImageResult]:
    """Generate an image using Flux Pro via fal.ai.

    ``reference_image_url`` is a previous *iteration* sketch of the same scene
    (img2img refinement). ``character_ref_image_url`` is a clean character
    portrait used for cross-scene character identity. If both are provided we
    prefer the per-iteration reference (refining a specific frame matters more
    in the moment).
    """
    if not settings.FAL_KEY:
        raise RuntimeError("FAL_KEY not configured")

    import fal_client

    final_prompt = _prepare_prompt(prompt)

    input_data: dict = {
        "prompt": final_prompt,
        "image_size": {"width": width, "height": height},
        "num_images": 1,
        "safety_tolerance": "5",
    }
    if seed is not None:
        input_data["seed"] = seed

    img_url = reference_image_url or character_ref_image_url
    if img_url:
        input_data["image_url"] = img_url
        # Iteration refinement should follow the previous frame closely; a
        # cross-scene character ref should bias only mildly toward the portrait.
        input_data["strength"] = 0.65 if reference_image_url else 0.35

    try:
        os.environ["FAL_KEY"] = settings.FAL_KEY
        result = fal_client.subscribe(
            "fal-ai/flux-pro/v1.1",
            arguments=input_data,
            with_logs=False,
        )

        images = result.get("images", [])
        if not images:
            raise RuntimeError("Fal returned no images")

        image_url = images[0]["url"]
        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()
        filePath = saveImage(img_response.content, settings.STATIC_DIR)
        return ImageResult(filePath=filePath, source="fal-flux-pro")
    except Exception as e:
        print(f"Fal Flux Pro failed: {e}")
        raise


def generateImageIdeogram(
    prompt: str,
    character_refs: list[dict] | None = None,
    seed: Optional[int] = None,
) -> Optional[ImageResult]:
    """Generate an image using Ideogram API with optional character reference for consistency."""
    if not settings.IDEOGRAM_API_KEY:
        raise RuntimeError("IDEOGRAM_API_KEY not configured")

    final_prompt = _prepare_prompt(prompt)

    url = "https://api.ideogram.ai/generate"
    headers = {
        "Api-Key": settings.IDEOGRAM_API_KEY,
        "Content-Type": "application/json",
    }

    image_request: dict = {
        "prompt": final_prompt,
        "aspect_ratio": "ASPECT_16_9",
        "model": "V_2",
        "style_type": "DESIGN",
        "negative_prompt": NEGATIVE_PROMPT,
    }
    if seed is not None:
        image_request["seed"] = seed

    payload = {"image_request": image_request}

    if character_refs:
        char_ref_images = []
        for ref in character_refs:
            if ref.get("image_url"):
                char_ref_images.append({"url": ref["image_url"]})
        if char_ref_images:
            payload["image_request"]["character_reference"] = {
                "character_images": char_ref_images[:4],  # API limit
            }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)

        if response.status_code == 401:
            raise RuntimeError("Ideogram authentication failed (401). Check IDEOGRAM_API_KEY.")
        if response.status_code >= 400:
            try:
                error_data = response.json()
            except Exception:
                error_data = response.text
            raise RuntimeError(f"Ideogram API HTTP {response.status_code}: {error_data}")

        data = response.json()
        images = data.get("data", [])
        if not images:
            raise RuntimeError("Ideogram returned no images")

        image_url = images[0].get("url")
        if not image_url:
            raise RuntimeError("Ideogram response missing image URL")

        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()
        filePath = saveImage(img_response.content, settings.STATIC_DIR)
        return ImageResult(filePath=filePath, source="ideogram")
    except Exception as e:
        print(f"Ideogram failed: {e}")
        raise


def _get_provider_order() -> list[str]:
    configured = [provider.strip().lower() for provider in settings.IMAGE_PROVIDER_ORDER.split(",") if provider.strip()]
    valid = [provider for provider in configured if provider in {"stability", "replicate", "fal", "ideogram"}]
    return valid or ["fal", "stability", "replicate"]


def _pick_primary_character_ref(
    character_refs: list[dict] | None,
    scene_text: Optional[str],
) -> Optional[dict]:
    """Pick the single character ref most likely to be the scene's POV subject.

    Heuristic: among refs whose name appears in the scene, return the one
    mentioned earliest (a proxy for "the character we open on / focus on").
    Returns None when zero or many refs are equally relevant — we don't want
    to bias the image toward a random secondary character.
    """
    if not character_refs:
        return None
    if not scene_text:
        return character_refs[0] if len(character_refs) == 1 else None

    import re as _re
    positions: list[tuple[int, dict]] = []
    for ref in character_refs:
        name = ref.get("name", "")
        if not name:
            continue
        m = _re.search(r"\b" + _re.escape(name) + r"\b", scene_text, _re.IGNORECASE)
        if m:
            positions.append((m.start(), ref))

    if not positions:
        return None
    positions.sort(key=lambda p: p[0])
    return positions[0][1]


def generateImage(
    prompt: str,
    reference_image_url: str | None = None,
    character_refs: list[dict] | None = None,
    seed: Optional[int] = None,
    scene_text: Optional[str] = None,
    strict_reference_mode: bool = False,
) -> ImageResult:
    """Generate a scene image with provider fallback.

    Parameters:
      - ``reference_image_url``: previous-iteration sketch URL for img2img refinement (within-scene consistency).
      - ``character_refs``: list of {name, description, image_url, seed} for characters the project knows about.
        When present, providers that support character conditioning are tried first.
      - ``seed``: deterministic seed (typically derived from project_id) so style/composition stays stable across scenes.
      - ``scene_text``: scene description used to pick the most relevant character ref for image-prompted providers.
      - ``strict_reference_mode``: when True and ``reference_image_url`` exists, only
        img2img-capable providers are allowed. This prevents silent fallback to
        text-only generation that breaks character continuity during refinement.
    """
    errors: list[str] = []
    providers = _get_provider_order()

    # Prefer Ideogram when we have character refs (it actually uses them).
    if character_refs and "ideogram" not in providers:
        providers = ["ideogram"] + providers

    # When refining with a reference image, prioritize providers that support img2img.
    if reference_image_url:
        img2img_providers = [p for p in providers if p in {"replicate", "fal", "ideogram"}]
        text_only_providers = [p for p in providers if p not in img2img_providers]
        providers = img2img_providers if strict_reference_mode else (img2img_providers + text_only_providers)

    primary_ref = _pick_primary_character_ref(character_refs, scene_text)
    primary_ref_url = primary_ref["image_url"] if primary_ref else None

    for provider in providers:
        try:
            if provider == "stability":
                result = generateImageStability(prompt, seed=seed)
            elif provider == "fal":
                result = generateImageFal(
                    prompt,
                    reference_image_url=reference_image_url,
                    character_ref_image_url=primary_ref_url,
                    seed=seed,
                )
            elif provider == "ideogram":
                result = generateImageIdeogram(prompt, character_refs=character_refs, seed=seed)
            else:
                result = generateImageReplicate(
                    prompt,
                    reference_image_url=reference_image_url,
                    seed=seed,
                )

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


def generateCharacterPortrait(
    name: str,
    description: str,
    seed: Optional[int] = None,
) -> Optional[ImageResult]:
    """Generate a clean reference portrait for one character (used at lock-time).

    Tries the configured providers in order but uses portrait aspect ratio and
    a focused single-subject prompt. Returns None if every provider fails — the
    caller should treat portrait generation as best-effort and not crash lock.
    """
    prompt = buildCharacterPortraitPrompt(name, description)
    providers = _get_provider_order()

    for provider in providers:
        try:
            if provider == "fal":
                return generateImageFal(prompt, seed=seed, width=768, height=1024)
            if provider == "stability":
                return generateImageStability(prompt, seed=seed, aspect_ratio="3:4")
            if provider == "replicate":
                return generateImageReplicate(prompt, seed=seed, width=768, height=1024)
            if provider == "ideogram":
                # Ideogram has no portrait aspect helper here; ASPECT_3_4 supported by API.
                if not settings.IDEOGRAM_API_KEY:
                    continue
                url = "https://api.ideogram.ai/generate"
                headers = {"Api-Key": settings.IDEOGRAM_API_KEY, "Content-Type": "application/json"}
                image_request: dict = {
                    "prompt": _prepare_prompt(prompt),
                    "aspect_ratio": "ASPECT_3_4",
                    "model": "V_2",
                    "style_type": "DESIGN",
                    "negative_prompt": NEGATIVE_PROMPT,
                }
                if seed is not None:
                    image_request["seed"] = seed
                resp = requests.post(url, headers=headers, json={"image_request": image_request}, timeout=90)
                if resp.status_code >= 400:
                    raise RuntimeError(f"Ideogram portrait HTTP {resp.status_code}: {resp.text}")
                data = resp.json().get("data", [])
                if not data or not data[0].get("url"):
                    raise RuntimeError("Ideogram portrait: no image returned")
                img_response = requests.get(data[0]["url"], timeout=30)
                img_response.raise_for_status()
                filePath = saveImage(img_response.content, settings.STATIC_DIR)
                return ImageResult(filePath=filePath, source="ideogram-portrait")
        except Exception as e:
            print(f"Portrait gen via {provider} failed: {e}")
            continue

    return None
