"""Push leaderboard CSV data to Grafana Cloud via Prometheus remote-write."""

from __future__ import annotations

import argparse
import csv
import logging
import struct
import sys
import time
from argparse import ArgumentDefaultsHelpFormatter
from pathlib import Path

import requests
import snappy

_DEFAULT_URL = "https://prometheus-prod-67-prod-us-west-0.grafana.net/api/v1/push"
_DEFAULT_USER_ID = "3125292"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Minimal protobuf encoder for the Prometheus remote-write WriteRequest schema.
# WriteRequest { repeated TimeSeries timeseries = 1; }
# TimeSeries   { repeated Label labels = 1; repeated Sample samples = 2; }
# Label        { string name = 1; string value = 2; }
# Sample       { double value = 1; int64 timestamp = 2; }
# ---------------------------------------------------------------------------

def _varint(n: int) -> bytes:
    out = []
    while True:
        bits = n & 0x7F
        n >>= 7
        if n:
            out.append(bits | 0x80)
        else:
            out.append(bits)
            break
    return bytes(out)


def _ldelim(field: int, data: bytes) -> bytes:
    return _varint(field << 3 | 2) + _varint(len(data)) + data


def _string(field: int, s: str) -> bytes:
    return _ldelim(field, s.encode())


def _double(field: int, v: float) -> bytes:
    return _varint(field << 3 | 1) + struct.pack("<d", v)


def _int64(field: int, v: int) -> bytes:
    return _varint(field << 3 | 0) + _varint(v)


def _encode_label(name: str, value: str) -> bytes:
    return _string(1, name) + _string(2, value)


def _encode_sample(value: float, timestamp_ms: int) -> bytes:
    return _double(1, value) + _int64(2, timestamp_ms)


def _encode_timeseries(labels: list[tuple[str, str]], value: float, timestamp_ms: int) -> bytes:
    label_fields = b"".join(_ldelim(1, _encode_label(n, v)) for n, v in labels)
    sample_field = _ldelim(2, _encode_sample(value, timestamp_ms))
    return label_fields + sample_field


def _build_payload(rows: list[dict], timestamp_ms: int) -> bytes:
    """Return snappy-compressed Prometheus WriteRequest protobuf bytes.

    Each numeric column becomes a separate metric named leaderboard_{column}
    with a 'repo' label identifying the repository.
    """
    series_fields = b""
    for row in rows:
        repo = row.get("repo", "").replace(" ", "_")
        for col, raw in row.items():
            if raw in ("", None):
                continue
            try:
                value = float(raw)
            except ValueError:
                continue
            labels = [("__name__", f"leaderboard_{col}"), ("repo", repo)]
            series_fields += _ldelim(1, _encode_timeseries(labels, value, timestamp_ms))
    return snappy.compress(series_fields)


def _read_token(token_file: Path) -> str:
    try:
        return token_file.read_text().strip()
    except FileNotFoundError:
        logger.error("Token file not found: %s", token_file)
        sys.exit(1)


def push(csv_file: Path, token_file: Path, url: str, user_id: str) -> None:
    rows = list(csv.DictReader(csv_file.read_text(encoding="utf-8").splitlines()))
    if not rows:
        logger.error("CSV file is empty: %s", csv_file)
        return
    if "repo" not in rows[0]:
        logger.error("CSV must contain a 'repo' column; found: %s", list(rows[0].keys()))
        return

    token = _read_token(token_file)
    timestamp_ms = int(time.time() * 1000)
    payload = _build_payload(rows, timestamp_ms)

    logger.debug("POSTing %d bytes (%d rows) to %s", len(payload), len(rows), url)
    response = requests.post(
        url,
        auth=(user_id, token),
        data=payload,
        headers={
            "Content-Type": "application/x-protobuf",
            "Content-Encoding": "snappy",
            "X-Prometheus-Remote-Write-Version": "0.1.0",
        },
    )

    if response.status_code in (200, 204):
        logger.info("Pushed %d rows from %s to Grafana", len(rows), csv_file)
    else:
        logger.error("Grafana push failed: %s %s", response.status_code, response.text)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Push CSV leaderboard data to Grafana Cloud.",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-i", "--input", default="leaderboard.csv", type=Path, help="Input CSV file")
    parser.add_argument("--token-file", default=".grafana_token", type=Path, help="File containing the Grafana API token")
    parser.add_argument("--url", default=_DEFAULT_URL, help="Grafana remote-write endpoint")
    parser.add_argument("--user-id", default=_DEFAULT_USER_ID, help="Grafana Cloud user/stack ID")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    ns = parser.parse_args()

    if ns.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not ns.input.exists():
        parser.error(f"File not found: {ns.input}")

    push(ns.input, ns.token_file, ns.url, ns.user_id)


if __name__ == "__main__":
    main()
