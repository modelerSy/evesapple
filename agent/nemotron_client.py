import json
import os
import httpx

from .prompts import SYSTEM_PROMPT
from backend.app.models import Claim, ClaimType

class MissingNvidiaApiKey(RuntimeError):
    pass

class NemotronResponseError(RuntimeError):
    pass

async def call_nemotron_json(content: str, *, budget: int | None = None, max_tokens: int = 4096, category: str = "", enable_thinking: bool = True, image_data_urls: list[str] | None = None) -> tuple[dict, str]:
    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    # Lightning is a text-only model. Use a multimodal model only for the
    # initial image-aware claim extraction; later research stages stay on the
    # existing text model.
    model_key = "NVIDIA_VISION_MODEL" if image_data_urls else "NVIDIA_MODEL"
    fallback_model = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning" if image_data_urls else "nvidia/nemotron-3.5-lightning-30b-a3b"
    model = os.getenv(model_key, fallback_model)
    reasoning_budget = budget if budget is not None else int(os.getenv("NVIDIA_REASONING_BUDGET", "2048"))
    base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
    if not api_key:
        raise MissingNvidiaApiKey("NVIDIA_API_KEY is not configured. Copy .env.example to .env and add the key.")
    user_content: str | list = content
    if image_data_urls:
        user_content = [{"type": "text", "text": content}] + [
            {"type": "image_url", "image_url": {"url": image_url}}
            for image_url in image_data_urls
        ]
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.format(category=category) if category else "Return JSON only and follow the user's requested schema exactly."},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,
        "top_p": 0.95,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "chat_template_kwargs": {"enable_thinking": enable_thinking},
        "reasoning_budget": reasoning_budget,
    }
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(f"{base_url}/chat/completions", headers={"Authorization": f"Bearer {api_key}"}, json=payload)
        if response.is_error:
            raise RuntimeError(f"NVIDIA API {response.status_code}: {response.text[:1000]}")
    raw = response.json()["choices"][0]["message"].get("content")
    if not raw or not raw.strip():
        raise NemotronResponseError("NVIDIA API returned no JSON content")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise NemotronResponseError("NVIDIA API returned malformed JSON") from exc
    return data, model

async def extract_claims(content: str, category: str) -> tuple[list[Claim], str]:
    data, model = await call_nemotron_json(content, max_tokens=4096, category=category)
    return [Claim(claim=item["claim"], type=ClaimType(item.get("type", "other")), verification_questions=item.get("verification_questions", [])) for item in data.get("claims", [])], model
