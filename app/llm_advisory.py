"""Optional Qwen (OpenAI-compatible, ModelScope) advisory layer.

The LLM only *refines* the template advice from app/advisory.py, which is passed
in as grounding. Any problem — no key, template mode, timeout, API error, bad
output — silently falls back to the template bullets. Diagnosis never depends on it.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Optional

from .advisory import get_advice
from .config import get_settings

log = logging.getLogger("cassavawatch.advisory")

CACHE_TTL_S = 3600
LOW_CONFIDENCE = 0.55
SYSTEM_PROMPT = (
    "You are an agricultural extension assistant for smallholder cassava farmers in East Africa. "
    "Give 3-4 short, practical bullet points. For CMD and CBSD, always emphasise removing infected "
    "plants and using certified clean cuttings, since these viruses spread mainly via planting material. "
    "Never recommend specific pesticide brands. If confidence is below 0.55, tell the farmer to "
    "photograph more leaves or consult an extension officer. Respond in {language} only. "
    "Plain language, no jargon."
)
LANG_NAMES = {"en": "English", "sw": "Swahili"}

_cache: dict = {}  # (disease, lang, bucket, model) -> (expires_at, bullets)
_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        st = get_settings()
        _client = OpenAI(base_url=st.qwen_base_url, api_key=st.qwen_api_key,
                         timeout=st.qwen_timeout_s, max_retries=0)
    return _client


def _bucket(confidence: float) -> str:
    return "low" if confidence < LOW_CONFIDENCE else "mid" if confidence < 0.8 else "high"


def _parse_bullets(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(?:[-*•·]|\d+[.)])\s*", "", line).strip().strip("*").strip()
        if line:
            out.append(line)
    return out[:4]


def _template(disease: str, lang: str) -> dict:
    return {"advice_bullets": get_advice(disease, lang)["bullets"], "source": "template"}


def generate_advice(disease: str, confidence: float, language: str = "en", n_leaves: int = 1,
                    lat: Optional[float] = None, lon: Optional[float] = None,
                    model: Optional[str] = None) -> dict:
    """-> {advice_bullets: list[str], source: "llm"|"template"}. Never raises."""
    lang = language if language in LANG_NAMES else "en"
    st = get_settings()
    t0 = time.perf_counter()
    if st.effective_advisory_mode != "llm":
        log.info("advice source=template reason=disabled latency_ms=0")
        return _template(disease, lang)
    model = model or st.qwen_model
    key = (disease, lang, _bucket(confidence), model)
    hit = _cache.get(key)
    if hit and hit[0] > time.time():
        log.info("advice source=llm cache=hit model=%s latency_ms=0", model)
        return {"advice_bullets": list(hit[1]), "source": "llm"}
    try:
        tmpl = get_advice(disease, lang)
        where = f" near lat {lat:.2f}, lon {lon:.2f}" if lat is not None and lon is not None else ""
        user = (f"Diagnosis: {tmpl['name']} (label '{disease}'), model confidence {confidence:.2f}, "
                f"from {n_leaves} leaf photo(s){where}.\n"
                f"Standard guidance to refine (do not contradict it):\n{tmpl['summary']}\n"
                + "\n".join(f"- {b}" for b in tmpl["bullets"])
                + f"\n\nFull note: {tmpl['text']}\n\nReply with 3-4 bullet points only, one per line, "
                  f"starting with '- '.")
        resp = _get_client().chat.completions.create(
            model=model, temperature=0.3, max_tokens=300,
            messages=[{"role": "system", "content": SYSTEM_PROMPT.format(language=LANG_NAMES[lang])},
                      {"role": "user", "content": user}],
            timeout=st.qwen_timeout_s)
        bullets = _parse_bullets(resp.choices[0].message.content or "")
        if len(bullets) < 2:
            raise ValueError(f"unusable LLM output: {bullets!r}")
        _cache[key] = (time.time() + CACHE_TTL_S, bullets)
        log.info("advice source=llm model=%s latency_ms=%d", model, (time.perf_counter() - t0) * 1000)
        return {"advice_bullets": bullets, "source": "llm"}
    except Exception as e:
        log.warning("advice source=template reason=%s: %s latency_ms=%d", type(e).__name__, e,
                    (time.perf_counter() - t0) * 1000)
        return _template(disease, lang)
