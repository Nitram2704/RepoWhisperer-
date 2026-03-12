from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

# For OpenAI-compatible providers
try:
    from openai import RateLimitError as OpenAIRateLimitError, APITimeoutError
except ImportError:
    OpenAIRateLimitError = Exception
    APITimeoutError = Exception

openai_retry = retry(
    retry=retry_if_exception_type((OpenAIRateLimitError, APITimeoutError)),
    wait=wait_exponential_jitter(initial=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)

# For Gemini (google-genai)
try:
    # google.genai uses standard error patterns or its own wrapper
    # We catch ClientError (usually includes 429) and ServerError
    from google.genai.errors import ClientError, APIError
except ImportError:
    ClientError = Exception
    APIError = Exception

gemini_retry = retry(
    # We retry on APIErrors (5xx) and specifically check for 429 in ClientError if needed
    # Usually tenacity works best filtering by types that represent transient failures
    retry=retry_if_exception_type((ClientError, APIError)),
    wait=wait_exponential_jitter(initial=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
