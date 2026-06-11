"""Labeled evaluation dataset (image -> ground-truth fields).

Stored as a small JSON file so it can grow over time. ``push_to_langsmith``
uploads it as a LangSmith dataset when an API key is configured; otherwise evals
run fully offline against this file.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "src" / "evals" / "labeled_receipts.json"

# Seed example uses the bundled Walmart receipt. Extend with more labeled images.
_SEED = [
    {
        "image_path": str(ROOT / "data" / "walmart-bon.jpeg"),
        "expected": {
            "business_personal": "personal",
            "payment_method": "Credit Card",
            "category": "Food",
        },
    }
]


def load_dataset() -> list[dict]:
    if DATASET_PATH.exists():
        return json.loads(DATASET_PATH.read_text())
    return _SEED


def save_seed() -> None:
    DATASET_PATH.write_text(json.dumps(_SEED, indent=2))


def push_to_langsmith(name: str = "expense-extraction") -> str | None:
    """Upload the dataset to LangSmith. Returns the dataset id, or None if no key."""
    from src.core.config import settings

    if not settings.langsmith_api_key:
        return None

    from langsmith import Client

    client = Client(api_key=settings.langsmith_api_key)
    if client.has_dataset(dataset_name=name):
        ds = client.read_dataset(dataset_name=name)
    else:
        ds = client.create_dataset(dataset_name=name)
    for example in load_dataset():
        client.create_example(
            inputs={"image_path": example["image_path"]},
            outputs=example["expected"],
            dataset_id=ds.id,
        )
    return str(ds.id)
