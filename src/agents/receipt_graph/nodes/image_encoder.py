"""Node: read the receipt image from disk and base64-encode it."""

from __future__ import annotations

import base64
from pathlib import Path

from src.agents.receipt_graph.state import ReceiptState


def encode_image(image_path: str) -> str:
    data = Path(image_path).read_bytes()
    return base64.b64encode(data).decode("utf-8")


def image_encoder_node(state: ReceiptState) -> dict:
    path = (state.get("image_path") or "").strip()
    if not path:
        return {"status": "failed", "error": "no image_path provided"}
    return {"image_base64": encode_image(path), "status": "processing"}
