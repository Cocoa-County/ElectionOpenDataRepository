from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def download_xlsx(url: str, destination_dir: Path, timeout_seconds: int) -> Path:
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

    filename = Path(parsed.path).name or "download.xlsx"
    if not filename.lower().endswith(".xlsx"):
        filename = f"{filename}.xlsx"

    destination = destination_dir / filename
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        content = response.read()

    if not content.startswith(b"PK"):
        prefix = content[:200].decode("utf-8", errors="replace")
        raise ValueError(
            "Downloaded content is not an XLSX file. "
            f"Response prefix: {prefix}"
        )

    destination.write_bytes(content)
    return destination
