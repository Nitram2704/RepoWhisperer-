# Phase 4: LLM Client - Research

**Researched:** 2026-03-10
**Domain:** Multi-provider LLM client, rate-limit handling, provider abstraction
**Confidence:** MEDIUM (rate limits verified via official docs; some limits are dashboard-only and change frequently)

---

## Summary

Phase 4 requires DocGen to query 4 LLM providers (Gemini, Groq, OpenRouter, DeepSeek) and produce raw Markdown documentation from retrieved code context. The core architectural insight is that **three of the four providers (Groq, OpenRouter, DeepSeek) expose an OpenAI-compatible API**. This means the `openai` Python SDK — with `base_url` overridden per provider — can serve as the single HTTP client for all four providers, avoiding provider-specific SDKs entirely. Gemini requires its own `google-generativeai` SDK since its wire format differs from the OpenAI protocol.

The retry problem is well-solved by `tenacity`, the ecosystem standard for Python retry logic. The `openai` SDK raises `openai.RateLimitError` for 429 responses, making it trivially catchable via `retry_if_exception_type`. The pattern of `wait_exponential_jitter + stop_after_attempt` is the correct approach; hand-rolling backoff logic is unnecessary and error-prone.

The critical practical constraint for this phase is that **free-tier quotas are very tight** (Gemini: 10 RPM / 250 RPD for Flash; Groq: 30 RPM / 1,000 RPD for 70B). A doc generation tool must batch carefully and stay well within these per-day limits, not just per-minute limits.

**Primary recommendation:** Use the `openai` Python SDK for Groq, OpenRouter, and DeepSeek (via `base_url` injection). Use `google-generativeai` SDK for Gemini. Wrap all provider calls in a single tenacity retry decorator. Implement a Provider Protocol/ABC with one concrete class per provider.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `openai` | >=1.0 | HTTP client for Groq, OpenRouter, DeepSeek | All three providers implement OpenAI wire format; one SDK covers three providers |
| `google-generativeai` | latest | HTTP client for Gemini | Official Google SDK; Gemini does not expose an OpenAI-compatible endpoint |
| `tenacity` | >=8.0 | Retry / exponential backoff | Ecosystem standard for Python retry logic; async-aware; decorator-based |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-dotenv` | any | Load env vars from `.env` file | Already likely in use from Phase 1 config.py |
| `pydantic` | >=2.0 | Validate provider config objects | If config.py grows to structured settings; optional for Phase 4 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `openai` SDK for Groq/OR/DeepSeek | `httpx` directly | httpx requires manual auth headers, response parsing, error mapping; openai SDK handles all this |
| `tenacity` | `backoff` library | `backoff` is simpler but less flexible; tenacity has jitter, async support, combined stop conditions |
| `tenacity` | Manual retry loop | Never hand-roll; misses jitter, thundering herd, proper async handling |
| `google-generativeai` | OpenAI SDK pointed at Gemini via proxy | Gemini's native API differs; proxy adds latency and complexity on free tier |

**Installation:**
```bash
uv add openai google-generativeai tenacity
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/docgen/
├── llm/
│   ├── __init__.py          # exports LLMClient factory
│   ├── base.py              # Provider Protocol / ABC
│   ├── gemini.py            # GeminiProvider
│   ├── groq.py              # GroqProvider
│   ├── openrouter.py        # OpenRouterProvider
│   ├── deepseek.py          # DeepSeekProvider
│   └── retry.py             # shared tenacity decorator factory
└── config.py                # already exists; extend for LLM config
```

### Pattern 1: Provider Protocol with openai SDK base_url injection

**What:** Each OpenAI-compatible provider is a thin wrapper that constructs an `openai.OpenAI` (or `AsyncOpenAI`) client with provider-specific `base_url` and `api_key`. All providers implement a common `complete(prompt: str, context: str) -> str` interface.

**When to use:** Whenever a provider exposes an OpenAI-compatible endpoint (Groq, OpenRouter, DeepSeek).

**Example:**
```python
# Source: openai Python SDK docs + provider documentation
from openai import OpenAI
import os

class GroqProvider:
    BASE_URL = "https://api.groq.com/openai/v1"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(self):
        self._client = OpenAI(
            api_key=os.environ["GROQ_API_KEY"],
            base_url=self.BASE_URL,
        )

    def complete(self, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(
            model=self.DEFAULT_MODEL,
            messages=messages,
        )
        return response.choices[0].message.content
```

Groq, OpenRouter, and DeepSeek all follow this same pattern — only `BASE_URL`, `DEFAULT_MODEL`, and the env var name differ.

### Pattern 2: Tenacity Retry Decorator for 429 Handling

**What:** A shared decorator applies exponential backoff with jitter on `openai.RateLimitError`. Applied once at the call site or as a wrapper method.

**When to use:** Wrap every `complete()` call. The same exception class (`openai.RateLimitError`) is raised by the SDK regardless of which OpenAI-compatible backend returned the 429.

**Example:**
```python
# Source: tenacity docs + OpenAI Cookbook rate-limit pattern
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)
from openai import RateLimitError

llm_retry = retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential_jitter(initial=1, max=60),
    stop=stop_after_attempt(6),
    reraise=True,
)

# Applied as decorator:
@llm_retry
def complete(self, messages):
    ...
```

For Gemini, the exception class differs — catch `google.api_core.exceptions.ResourceExhausted` (maps to HTTP 429) and include it in `retry_if_exception_type`.

### Pattern 3: Provider Factory via Config

**What:** `config.py` reads `DOCGEN_PROVIDER` env var (or config file value) and returns the appropriate provider instance. The rest of DocGen only imports `get_provider()` and calls `.complete()`.

**When to use:** Satisfies LLM-06 (configurable provider) without conditional logic scattered through the codebase.

**Example:**
```python
# Source: standard strategy/factory pattern
PROVIDERS = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "openrouter": OpenRouterProvider,
    "deepseek": DeepSeekProvider,
}

def get_provider() -> BaseProvider:
    name = os.getenv("DOCGEN_PROVIDER", "gemini")
    if name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {name}. Choose from: {list(PROVIDERS)}")
    return PROVIDERS[name]()
```

### Anti-Patterns to Avoid

- **One SDK per provider:** Avoid importing `groq`, `deepseek`, `openrouter` Python SDKs. They all implement the OpenAI wire format — use the `openai` SDK with `base_url` instead.
- **Retry in a while loop:** Never write `while attempts < MAX: try: ... except: sleep(n)`. Use tenacity.
- **Shared global client:** Do not instantiate providers at module import time. Instantiate when `get_provider()` is called, so env vars are read at runtime.
- **Catching bare `Exception` in retry:** Only retry `RateLimitError` (429). Retrying `AuthenticationError` or `BadRequestError` is wasteful and masks bugs.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Exponential backoff | Custom sleep loop | `tenacity` | Misses jitter (thundering herd), no async support, no stop conditions |
| Multi-provider HTTP | Provider-specific HTTP calls | `openai` SDK + `base_url` | SDK handles auth headers, response parsing, error type mapping |
| Config file parsing | Custom INI/JSON reader | `python-dotenv` + env vars | Already established in Phase 1 config.py |
| Token counting | Counting characters / words | Stay well under context window | Free-tier context windows (1M tokens) are massive; 8K token target per request is safe without counting |

**Key insight:** Three of four providers are OpenAI-compatible. The openai Python SDK is the correct abstraction layer — it is not "OpenAI-specific", it is the de facto standard protocol SDK.

---

## Provider Reference

### Gemini (LLM-01)

| Item | Value | Confidence |
|------|-------|-----------|
| SDK | `google-generativeai` | HIGH |
| API model ID | `gemini-2.5-flash` (recommended), `gemini-2.5-flash-lite` (higher RPD) | HIGH — from official docs |
| Context window | 1,048,576 tokens input / 65,536 output | HIGH |
| Free RPM | 10 (Flash), 15 (Flash-Lite) | MEDIUM — from third-party aggregator; verify at aistudio.google.com/rate-limit |
| Free RPD | 250 (Flash), 1,000 (Flash-Lite) | MEDIUM — same source; Google cut limits 50-80% in Dec 2025 |
| Free TPM | 250,000 | MEDIUM |
| Rate limit exception | `google.api_core.exceptions.ResourceExhausted` | MEDIUM |
| Auth env var | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | HIGH |
| Note | Limits apply per project, not per API key | HIGH |

**Warning:** The `gemini-2.0-flash` model retires June 1, 2026. Do not use it. The `gemini-1.5-*` models in the existing RESEARCH.md are outdated.

### Groq (LLM-02)

| Item | Value | Confidence |
|------|-------|-----------|
| SDK | `openai` (base_url override) | HIGH |
| Base URL | `https://api.groq.com/openai/v1` | HIGH — from official Groq docs |
| Recommended model | `llama-3.3-70b-versatile` (quality), `llama-3.1-8b-instant` (speed/volume) | HIGH — verified at console.groq.com/docs/models |
| Context window | 131,072 tokens (both models) | HIGH |
| Free RPM | 30 (both models) | HIGH — from console.groq.com/docs/rate-limits |
| Free TPM | 12,000 (70B), 6,000 (8B) | HIGH — from official rate-limits page |
| Free RPD | 1,000 (70B), 14,400 (8B) | HIGH |
| Rate limit exception | `openai.RateLimitError` | HIGH |
| Auth env var | `GROQ_API_KEY` | HIGH |
| Note | Old model IDs `llama3-70b-8192` and `mixtral-8x7b-32768` are deprecated — DO NOT USE | HIGH |

**Warning:** The existing RESEARCH.md lists `llama3-70b-8192` and `mixtral-8x7b-32768`. These are outdated model identifiers. Use `llama-3.3-70b-versatile` and `llama-3.1-8b-instant`.

### OpenRouter (LLM-03)

| Item | Value | Confidence |
|------|-------|-----------|
| SDK | `openai` (base_url override) | HIGH |
| Base URL | `https://openrouter.ai/api/v1` | HIGH — from official docs |
| Auth env var | `OPENROUTER_API_KEY` | HIGH |
| Free models | Multiple (rotate based on `:free` suffix models) | MEDIUM |
| Rate limits | Not publicly documented for free tier | LOW — no official source found |
| Optional headers | `HTTP-Referer` (site URL), `X-Title` (app name) | HIGH — from docs, used for attribution |
| Rate limit exception | `openai.RateLimitError` | HIGH |
| Note | Free models have lower limits and may be queued behind paid requests | MEDIUM |

**Usage pattern:** OpenRouter free-tier model IDs follow the pattern `provider/model:free` (e.g., `meta-llama/llama-3.3-70b-instruct:free`). The active model should be configurable via env var (`DOCGEN_OPENROUTER_MODEL`).

### DeepSeek (LLM-04)

| Item | Value | Confidence |
|------|-------|-----------|
| SDK | `openai` (base_url override) | HIGH |
| Base URL | `https://api.deepseek.com` or `https://api.deepseek.com/v1` | HIGH — from official docs |
| Model IDs | `deepseek-chat` (V3.2), `deepseek-reasoner` (thinking mode) | HIGH |
| Context window | 128,000 tokens | HIGH |
| Rate limits | Not published — DeepSeek explicitly states no RPM/TPM constraints | HIGH — from official rate_limit docs |
| Auth env var | `DEEPSEEK_API_KEY` | HIGH |
| Free tier | DeepSeek operates pay-as-you-go; no explicit free tier with hard limits | MEDIUM |
| Rate limit exception | `openai.RateLimitError` | HIGH (if 429 occurs despite no stated limits) |

---

## Common Pitfalls

### Pitfall 1: Using Stale Model IDs

**What goes wrong:** Code uses deprecated model names like `gemini-1.5-flash`, `llama3-70b-8192`, `mixtral-8x7b-32768`. Provider returns 404 or model-not-found error.
**Why it happens:** LLM model names change frequently; cached knowledge is stale.
**How to avoid:** Make model IDs configurable via env var (e.g., `DOCGEN_GEMINI_MODEL`, `DOCGEN_GROQ_MODEL`) with sensible defaults that can be overridden without code changes.
**Warning signs:** `404 model not found` or `invalid model` errors at runtime.

### Pitfall 2: Hitting Daily Limits (RPD), Not Just RPM

**What goes wrong:** Rate limiting logic only handles RPM (per-minute). The tool works in short sessions but fails in CI or batch runs that exhaust the daily quota (RPD).
**Why it happens:** RPD is less visible than RPM; tenacity retries cannot recover from RPD exhaustion within the same day.
**How to avoid:** Log total requests per provider per run. Warn when approaching 80% of estimated daily limit. The Gemini Flash limit of 250 RPD means at most 250 documentation generation calls per day.

### Pitfall 3: Retrying Non-Retryable Errors

**What goes wrong:** Broad exception catching retries auth errors, bad request errors, or model-not-found errors — wasting time and confusing diagnostics.
**Why it happens:** Lazy `except Exception` in retry configuration.
**How to avoid:** Only retry `RateLimitError` (429) and optionally `APITimeoutError` (408). Let `AuthenticationError` (401) and `BadRequestError` (400) propagate immediately.

### Pitfall 4: Gemini Exception Class Mismatch

**What goes wrong:** Applying the `openai.RateLimitError` retry only to Groq/OR/DeepSeek but forgetting Gemini uses a different SDK with different exception classes.
**Why it happens:** Mixed SDK landscape.
**How to avoid:** Gemini 429s raise `google.api_core.exceptions.ResourceExhausted`. The tenacity decorator for Gemini must catch this class, not `openai.RateLimitError`. Define separate retry decorators per SDK family, or catch both in one decorator.

### Pitfall 5: Gemini Rate Limits Apply Per Project, Not Per Key

**What goes wrong:** Developer generates multiple API keys thinking this increases quota. It does not — limits apply per Google Cloud project.
**Why it happens:** Misunderstanding of how Google quotas work.
**How to avoid:** Document this clearly. A single `GEMINI_API_KEY` is sufficient; multiple keys from the same project share the quota.

---

## Code Examples

### Verified Patterns

#### OpenAI-compatible provider (Groq example)
```python
# Pattern: openai SDK with base_url override
# Source: openai Python SDK docs, Groq GroqDocs quickstart
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
)
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Generate docs for this code..."}],
)
text = response.choices[0].message.content
```

#### DeepSeek (same pattern, different base_url)
```python
# Source: api-docs.deepseek.com
client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "..."}],
)
```

#### OpenRouter (same pattern + optional attribution headers)
```python
# Source: openrouter.ai/docs/quickstart
import httpx
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://github.com/your/docgen",
        "X-Title": "DocGen",
    },
)
```

#### Tenacity retry decorator (for OpenAI-compatible providers)
```python
# Source: tenacity readthedocs, OpenAI Cookbook rate-limit guide
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter
from openai import RateLimitError, APITimeoutError

openai_retry = retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
    wait=wait_exponential_jitter(initial=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
```

#### Tenacity retry decorator (for Gemini)
```python
# Source: tenacity docs + google-api-core exception hierarchy
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter
from google.api_core.exceptions import ResourceExhausted, DeadlineExceeded

gemini_retry = retry(
    retry=retry_if_exception_type((ResourceExhausted, DeadlineExceeded)),
    wait=wait_exponential_jitter(initial=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
```

#### Provider factory
```python
# Source: standard strategy pattern
import os
from typing import Protocol

class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> str: ...

def get_provider() -> LLMProvider:
    name = os.getenv("DOCGEN_PROVIDER", "gemini").lower()
    providers = {
        "gemini": GeminiProvider,
        "groq": GroqProvider,
        "openrouter": OpenRouterProvider,
        "deepseek": DeepSeekProvider,
    }
    if name not in providers:
        raise SystemExit(f"Unknown DOCGEN_PROVIDER={name!r}. Valid: {list(providers)}")
    return providers[name]()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `gemini-1.5-flash` / `gemini-1.5-pro` | `gemini-2.5-flash` / `gemini-2.5-flash-lite` | 2025 | Old IDs likely still work but are outdated; 2.5 is the current free-tier generation |
| `gemini-2.0-flash` | `gemini-2.5-flash` | Retirement June 2026 | Do not use 2.0; plan to use 2.5 |
| `llama3-70b-8192` (Groq) | `llama-3.3-70b-versatile` | 2024-2025 | Old ID deprecated on Groq |
| `mixtral-8x7b-32768` (Groq) | Removed from Groq free tier | 2025 | No longer available |
| Separate HTTP clients per provider | `openai` SDK + `base_url` | 2024 | Groq, OR, DeepSeek all adopted OpenAI wire format |

**Deprecated/outdated (from existing RESEARCH.md):**
- `gemini-1.5-flash`: Replaced by `gemini-2.5-flash`
- `llama3-70b-8192`: Replaced by `llama-3.3-70b-versatile`
- `mixtral-8x7b-32768`: No longer available on Groq free tier

---

## Open Questions

1. **Gemini exact free-tier RPM/RPD as of March 2026**
   - What we know: Third-party sources (aifreeapi.com) report 10 RPM / 250 RPD for Flash, but Google's official docs defer to the AI Studio dashboard
   - What's unclear: Whether Dec 2025 quota cuts were the final change or if further changes occurred in early 2026
   - Recommendation: Verify at https://aistudio.google.com/rate-limit before hardcoding retry wait times. Design wait times conservatively (min 6 seconds between Gemini requests when at free tier).

2. **OpenRouter free-tier rate limits**
   - What we know: Free models exist; paid requests get priority; no published RPM/TPM for free tier
   - What's unclear: Whether there is a hard cap or just soft deprioritization
   - Recommendation: Default to conservative retry (same tenacity settings as other providers); treat OpenRouter as a secondary/fallback provider. Do not promise reliability on free tier.

3. **Gemini SDK version and exact exception class path**
   - What we know: `google.api_core.exceptions.ResourceExhausted` is the standard 429 exception in google-cloud libraries
   - What's unclear: Whether `google-generativeai` SDK re-exports this or wraps it differently
   - Recommendation: In implementation, print the exception type in a test before finalizing the retry decorator. Alternatively, also catch `Exception` subclass by checking `e.grpc_status_code` or `e.code()`.

---

## Sources

### Primary (HIGH confidence)
- `https://console.groq.com/docs/rate-limits` — Groq free-tier rate limits table fetched directly; all Groq values in this document
- `https://console.groq.com/docs/models` — Groq model IDs, context windows, speed ratings
- `https://api-docs.deepseek.com/quick_start/rate_limit` — DeepSeek rate limit policy ("no constraints" statement)
- `https://api-docs.deepseek.com/` — DeepSeek model IDs, base URL, auth method
- `https://openrouter.ai/docs/quickstart` — OpenRouter base URL, auth format, optional headers
- `https://tenacity.readthedocs.io/en/latest/api.html` — tenacity wait strategies, stop conditions, async support
- `https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash` — Gemini 2.5 Flash model ID, context window

### Secondary (MEDIUM confidence)
- `https://www.aifreeapi.com/en/posts/gemini-api-free-tier-rate-limits` — Gemini free-tier RPM/RPD table (third-party aggregator, cross-referenced with search results from multiple sources)
- `https://github.com/openai/openai-cookbook` (referenced in search) — OpenAI rate-limit handling pattern with tenacity
- `https://developers.openai.com/cookbook/examples/how_to_handle_rate_limits/` — tenacity + RateLimitError pattern

### Tertiary (LOW confidence — flag for validation)
- OpenRouter free-tier rate limits: No official source found; behavior described as "queued behind paid" from search results only

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — openai SDK + google-generativeai is the obvious and verified choice
- Groq model IDs and rate limits: HIGH — fetched directly from official Groq docs
- Gemini model IDs: HIGH — from official Google AI docs
- Gemini free-tier rate limits: MEDIUM — official docs defer to dashboard; third-party aggregator used
- DeepSeek rate limits: HIGH — official docs explicitly state no constraints
- OpenRouter rate limits: LOW — no official published limits found
- Architecture patterns: HIGH — standard strategy/factory pattern, well-established
- Retry/tenacity: HIGH — official docs verified

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (rate limits change frequently; re-verify Gemini limits before implementation)
