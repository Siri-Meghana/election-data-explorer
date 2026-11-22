"""Small helper for calling the OpenFEC API with retries and useful errors."""

import time

import requests
from django.conf import settings
from django.core.management.base import CommandError

RETRY_STATUSES = (502, 503, 504)  # temporary server-side problems
MAX_ATTEMPTS = 4


def fec_get(path, params):
    """GET {FEC_API_BASE_URL}/{path} and return parsed JSON.

    Retries a few times (with growing pauses) when the FEC is slow or
    temporarily unavailable. On failure raises CommandError that includes the
    API's own error body, so a rejected parameter (422) or a rate limit (429)
    is easy to read.
    """
    url = f"{settings.FEC_API_BASE_URL}/{path.lstrip('/')}"
    response = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(url, params=params, timeout=60)
        except requests.RequestException as exc:
            if attempt == MAX_ATTEMPTS:
                raise CommandError(f"Could not reach the FEC API: {exc}")
        else:
            if response.status_code not in RETRY_STATUSES:
                break
            if attempt == MAX_ATTEMPTS:
                raise CommandError(
                    f"The FEC server timed out or was unavailable "
                    f"(HTTP {response.status_code}) after {MAX_ATTEMPTS} tries. "
                    f"This is on the FEC's side. Try again in a few minutes, or "
                    f"make the request smaller (for example "
                    f"add --state XX or lower --max-pages)."
                )
        wait = 3 * attempt
        print(f"  FEC is slow or busy (attempt {attempt} of {MAX_ATTEMPTS}); "
              f"retrying in {wait}s...")
        time.sleep(wait)

    if response.status_code == 429:
        raise CommandError(
            "FEC API rate limit hit (HTTP 429). Use your own free API key "
            "instead of DEMO_KEY, or wait and retry."
        )
    if not response.ok:
        raise CommandError(
            f"FEC API returned HTTP {response.status_code}: {response.text[:500]}"
        )
    return response.json()
