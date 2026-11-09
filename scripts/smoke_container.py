"""Smoke-test a running container through its public HTTP interface."""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request


def probe_pdf() -> bytes:
    content = b"BT /F1 18 Tf 72 700 Td (EasyRead container smoke test.) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(data)


def read_json(url: str, timeout: float = 10) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read())


def wait_ready(base: str, deadline: float) -> dict:
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return read_json(base + "/api/version")
        except (OSError, ValueError, urllib.error.HTTPError) as error:
            last_error = error
            time.sleep(0.5)
    raise RuntimeError(f"container did not become ready: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18765")
    parser.add_argument("--version", required=True)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    base = args.url.rstrip("/")
    deadline = time.monotonic() + args.timeout

    version = wait_ready(base, deadline)
    if version.get("version") != args.version:
        raise RuntimeError(f"container version is {version.get('version')}, expected {args.version}")

    library = read_json(base + "/api/library")
    request = urllib.request.Request(
        base + "/api/import?name=container-smoke.pdf&translate=0",
        data=probe_pdf(),
        headers={"Content-Type": "application/pdf", "X-Token": library["token"]},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        imported = json.loads(response.read())
    paper_id = imported["id"]

    state = {}
    while time.monotonic() < deadline:
        state = read_json(f"{base}/api/p/{paper_id}/state", timeout=15)
        job = state.get("job") or {}
        if job.get("state") in ("done", "partial", "error", "cancelled"):
            break
        time.sleep(0.5)
    job = state.get("job") or {}
    if job.get("state") != "done":
        raise RuntimeError(f"PDF import did not finish: {job}")
    pages = ((state.get("paper") or {}).get("meta") or {}).get("pages") or []
    if len(pages) != 1:
        raise RuntimeError(f"expected one rendered page, got {len(pages)}")
    with urllib.request.urlopen(f"{base}/p/{paper_id}/{pages[0]['img']}?w=1000", timeout=30) as response:
        image = response.read(12)
    if image[:4] != b"RIFF" or image[8:12] != b"WEBP":
        raise RuntimeError("rendered page is not WebP")
    print(f"PASS: EasyRead {args.version}, HTTP API, persistent library and PDF rendering")


if __name__ == "__main__":
    main()
