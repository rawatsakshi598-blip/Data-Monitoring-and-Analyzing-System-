"""
LLM Client with automatic provider fallback.
"""

import json
import urllib.request
import urllib.error
import os
import re
import time

_PROVIDERS = None


def _get_providers():
    global _PROVIDERS
    if _PROVIDERS is None:
        _PROVIDERS = []
        key = os.environ.get("LLM_API_KEY", "")
        if key:
            _PROVIDERS.append(
                {
                    "name": "primary",
                    "api_key": key,
                    "base_url": os.environ.get("LLM_BASE_URL", ""),
                    "model": os.environ.get("LLM_MODEL", ""),
                }
            )
        for i in range(1, 6):
            key = os.environ.get(f"LLM_FALLBACK_{i}_API_KEY", "")
            if key:
                _PROVIDERS.append(
                    {
                        "name": f"fallback_{i}",
                        "api_key": key,
                        "base_url": os.environ.get(f"LLM_FALLBACK_{i}_BASE_URL", ""),
                        "model": os.environ.get(f"LLM_FALLBACK_{i}_MODEL", ""),
                    }
                )
        print(
            f"[LLM] Loaded {len(_PROVIDERS)} providers: {[p['name']+'('+p['model']+')' for p in _PROVIDERS]}"
        )
    return _PROVIDERS


def _call_single_provider(
    provider, system_prompt, user_prompt, temperature, max_tokens, timeout=30
):
    url = f"{provider['base_url'].rstrip('/')}/chat/completions"
    payload = json.dumps(
        {
            "model": provider["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {provider['api_key']}",
            "User-Agent": "Mozilla/5.0 (compatible; DataGuard/1.0)",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            message = data["choices"][0]["message"]
            content = message.get("content", "")
            if content:
                return content, None
            reasoning = message.get("reasoning_content", "")
            if reasoning:
                json_match = re.search(r"\{[^{}]*\}", reasoning)
                if json_match:
                    return json_match.group(0), None
            return None, "Empty response from LLM"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if e.code == 429:
            return None, "RATE_LIMIT"
        return None, f"HTTP {e.code}: {body[:150]}"
    except Exception as e:
        return None, f"Connection error: {e}"


def call_llm(system_prompt, user_prompt, temperature=0.3, max_tokens=4096):
    providers = _get_providers()
    if not providers:
        print("[LLM] ❌ No providers configured")
        return None

    for i, provider in enumerate(providers):
        print(f"[LLM] 🔄 Trying {provider['name']} ({provider['model']})...")
        response, error = _call_single_provider(
            provider, system_prompt, user_prompt, temperature, max_tokens, timeout=30
        )

        if response is not None:
            print(f"[LLM] ✅ {provider['name']} succeeded ({provider['model']})")
            return response

        is_rate_limit = "RATE_LIMIT" in (error or "")
        is_connection = "Connection error" in (error or "") or "timed out" in (
            error or ""
        )

        if is_rate_limit or is_connection:
            label = "rate limited" if is_rate_limit else "connection error"
            next_info = (
                f"→ trying {providers[i+1]['name']}"
                if i + 1 < len(providers)
                else "→ no more providers"
            )
            print(f"[LLM] ⚠️ {provider['name']} {label}, {next_info}")
            time.sleep(1)
        else:
            print(f"[LLM] ⚠️ {provider['name']} error: {error}")
            if i + 1 < len(providers):
                print(
                    f"[LLM] → trying {providers[i+1]['name']} ({providers[i+1]['model']})"
                )

    print(f"[LLM] ❌ All {len(providers)} providers failed")
    return None


def extract_json(response):
    """Extract JSON from LLM response - handles markdown, nested objects, escaped newlines."""
    if not response:
        return None

    text = response.strip()

    # Remove markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1].strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the outermost JSON object using brace matching
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False
    end = -1

    for idx in range(start, len(text)):
        ch = text[idx]
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = idx + 1
                    break

    if end == -1:
        return None

    candidate = text[start:end]

    # Try parsing the candidate
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Last resort: clean up common issues
    try:
        # Replace actual newlines in string values with \n
        cleaned = re.sub(r"(?<!\\)\n", "\\n", candidate)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    return None


def get_provider_status():
    providers = _get_providers()
    return [
        {"name": p["name"], "model": p["model"], "base_url": p["base_url"]}
        for p in providers
    ]
