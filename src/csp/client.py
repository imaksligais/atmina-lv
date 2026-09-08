"""CSP PxWeb API v1 client and JSON-stat2 parser."""
import logging
import time

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://data.stat.gov.lv/api/v1/lv/OSP_PUB/START"
TIMEOUT = 30
MAX_RETRIES = 3
RATE_LIMIT_SEC = 1.0

_last_request_time = 0.0


def fetch_table(path: str, query: list[dict], format: str = "json-stat2") -> dict:
    """POST to PxWeb API and return parsed JSON response.

    Args:
        path: Table path after START/, e.g. "EMP/NBBA/NVA/NVA011m"
        query: List of dimension selection dicts
        format: Response format, default "json-stat2"

    Returns:
        Parsed JSON-stat2 response dict

    Raises:
        httpx.HTTPStatusError: On non-2xx response after retries
    """
    global _last_request_time

    url = f"{BASE_URL}/{path}"
    body = {"query": query, "response": {"format": format}}

    for attempt in range(MAX_RETRIES):
        # Rate limiting
        elapsed = time.time() - _last_request_time
        if elapsed < RATE_LIMIT_SEC:
            time.sleep(RATE_LIMIT_SEC - elapsed)

        try:
            _last_request_time = time.time()
            resp = httpx.post(url, json=body, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPStatusError, httpx.TransportError) as e:
            wait = 2 ** attempt
            logger.warning("CSP API attempt %d failed: %s. Retry in %ds", attempt + 1, e, wait)
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(wait)

    return {}  # unreachable


def parse_jsonstat2(data: dict) -> list[dict]:
    """Parse a JSON-stat2 response into flat row dicts.

    Handles 2D (ContentsCode x TIME) and 3+D responses.
    Non-TIME, non-ContentsCode dimensions become the 'breakdown' field.

    Returns list of dicts with keys:
        indicator, period, value, breakdown, updated
    """
    dim_ids = data["id"]       # e.g. ["GRS_NET", "ContentsCode", "TIME"]
    sizes = data["size"]       # e.g. [2, 1, 2]
    values = data["value"]
    updated = data.get("updated", "")

    # Build ordered code lists for each dimension
    dim_codes: list[list[str]] = []
    for dim_id in dim_ids:
        cat = data["dimension"][dim_id]["category"]
        index_map = cat["index"]  # {"GRS": 0, "NET": 1}
        codes = sorted(index_map.keys(), key=lambda k: index_map[k])
        dim_codes.append(codes)

    # Find special dimension positions
    time_idx = dim_ids.index("TIME")
    contents_idx = dim_ids.index("ContentsCode") if "ContentsCode" in dim_ids else None

    # Determine breakdown dimension (first dim that isn't TIME or ContentsCode)
    breakdown_idx = None
    for i, dim_id in enumerate(dim_ids):
        if dim_id not in ("TIME", "ContentsCode"):
            breakdown_idx = i
            break

    # Iterate over all combinations using row-major order
    rows = []
    for flat_i in range(len(values)):
        # Decompose: for sizes [2, 1, 2], flat_i=3 -> [1, 0, 1]
        indices = []
        remainder = flat_i
        for _s in sizes:
            stride = 1
            for s2 in sizes[len(indices) + 1:]:
                stride *= s2
            idx = remainder // stride
            remainder = remainder % stride
            indices.append(idx)

        period = dim_codes[time_idx][indices[time_idx]]

        if contents_idx is not None:
            indicator = dim_codes[contents_idx][indices[contents_idx]]
        else:
            indicator = "_default_"

        if breakdown_idx is not None:
            breakdown = dim_codes[breakdown_idx][indices[breakdown_idx]]
        else:
            breakdown = "_total_"

        val = values[flat_i]

        rows.append({
            "indicator": indicator,
            "period": period,
            "value": val,
            "breakdown": breakdown,
            "updated": updated,
        })

    return rows
