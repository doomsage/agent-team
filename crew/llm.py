"""LLM calls: Groq (cloud, free tier) + Ollama (local). Dono OpenAI-compatible hain."""
import json
import os
import time

import requests


def load_env(path=".env"):
    """Simple .env loader (extra library ki zaroorat nahi)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class LLMError(Exception):
    pass


def _endpoint(provider, cfg):
    if provider == "groq":
        base = os.environ.get("GROQ_BASE_URL") or cfg["groq_base_url"]
        key = os.environ.get("GROQ_API_KEY", "")
        if not key or "yaha_apni_key" in key:
            raise LLMError(
                "GROQ_API_KEY set nahi hai. .env file kholo aur console.groq.com/keys "
                "se banayi hui free key paste karo."
            )
        return base, {"Authorization": "Bearer " + key}
    base = os.environ.get("OLLAMA_BASE_URL") or cfg["ollama_base_url"]
    return base, {"Authorization": "Bearer ollama"}


def chat(provider_cfg, cfg, messages, temperature=0.6, max_tokens=6000, retries=3):
    """Ek chat completion call. provider_cfg = config['models'][role]."""
    provider = provider_cfg["provider"]
    model = provider_cfg["model"]
    base, headers = _endpoint(provider, cfg)
    url = base.rstrip("/") + "/chat/completions"
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=180)
            if r.status_code == 429:
                wait = 20 * (attempt + 1)
                print(f"    [{provider}] rate limit, {wait}s ruk ke retry...")
                time.sleep(wait)
                continue
            if r.status_code >= 400:
                raise LLMError(f"{provider} error {r.status_code}: {r.text[:300]}")
            data = r.json()
            content = data["choices"][0]["message"].get("content") or ""
            if not content.strip():
                raise LLMError(f"{provider} ne khaali jawab diya (model busy ho sakta hai)")
            return content
        except requests.ConnectionError as e:
            last_err = e
            if provider == "ollama":
                raise LLMError(
                    "Ollama se connect nahi hua. Check karo: Ollama chal raha hai? "
                    "(system tray me icon / `ollama list` command)"
                )
            time.sleep(5)
        except requests.Timeout:
            last_err = "timeout"
            time.sleep(5)
    raise LLMError(f"{provider} call fail hua retries ke baad: {last_err}")


def list_models(provider, cfg):
    """--check ke liye: provider ke available models."""
    base, headers = _endpoint(provider, cfg)
    r = requests.get(base.rstrip("/") + "/models", headers=headers, timeout=30)
    r.raise_for_status()
    return [m["id"] for m in r.json().get("data", [])]
