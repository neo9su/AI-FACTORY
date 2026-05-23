import logging
import secrets
import string
from threading import Lock
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, AnyHttpUrl, field_validator

logger = logging.getLogger(__name__)

app = FastAPI(title="URL Shortener API", version="1.0.0")

# In-memory storage: short_code -> (original_url, click_count)
storage: Dict[str, tuple[str, int]] = {}
storage_lock = Lock()

CODE_LENGTH = 6
MAX_URL_LENGTH = 2048
ALPHABET = string.ascii_letters + string.digits


class ShortenRequest(BaseModel):
    long_url: AnyHttpUrl

    @field_validator("long_url")
    @classmethod
    def check_url_length(cls, v: AnyHttpUrl) -> AnyHttpUrl:
        url_str = str(v)
        if len(url_str) > MAX_URL_LENGTH:
            raise ValueError(f"URL must not exceed {MAX_URL_LENGTH} characters")
        return v


class ShortenResponse(BaseModel):
    short_code: str


class StatsResponse(BaseModel):
    original_url: str
    click_count: int


def generate_short_code() -> str:
    """Generate a random alphanumeric short code of length CODE_LENGTH."""
    return ''.join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def generate_unique_code() -> str:
    """Generate a unique short code with collision retry."""
    with storage_lock:
        for _ in range(100):  # limit retries to avoid infinite loop
            code = generate_short_code()
            if code not in storage:
                return code
        # Extremely unlikely collision after 100 attempts; raise error
        raise RuntimeError("Failed to generate unique short code after 100 attempts")


@app.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
def shorten_url(request: ShortenRequest):
    """
    Accept a long URL and return a short code.
    """
    long_url_str = str(request.long_url)
    code = generate_unique_code()
    with storage_lock:
        storage[code] = (long_url_str, 0)
    logger.info("Created short code %s for URL %s", code, long_url_str)
    return ShortenResponse(short_code=code)


@app.get("/{code}", status_code=status.HTTP_302_FOUND)
def redirect_to_original(code: str):
    """
    Redirect to the original URL for the given short code.
    Increments click count.
    """
    with storage_lock:
        entry = storage.get(code)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short code not found")
        original_url, click_count = entry
        storage[code] = (original_url, click_count + 1)
    logger.info("Redirecting code %s to %s (click #%d)", code, original_url, click_count + 1)
    return RedirectResponse(url=original_url, status_code=status.HTTP_302_FOUND)


@app.get("/stats/{code}", response_model=StatsResponse)
def get_stats(code: str):
    """
    Return click count and original URL for the given short code.
    """
    with storage_lock:
        entry = storage.get(code)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short code not found")
        original_url, click_count = entry
    return StatsResponse(original_url=original_url, click_count=click_count)
