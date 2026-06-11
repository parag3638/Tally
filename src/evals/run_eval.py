"""Run the receipt-extraction eval.

Offline mode (default): runs the real extractor over the labeled dataset and
prints field-level accuracy. Requires OPENAI/ANTHROPIC keys to call the model.

    python -m src.evals.run_eval                 # run + print metrics
    python -m src.evals.run_eval --push          # also push dataset to LangSmith

The pure scoring functions in ``evaluators.py`` are covered by unit tests so the
metric logic is verified without any API calls.
"""

from __future__ import annotations

import argparse
import json

from src.core.logging import configure_logging, get_logger
from src.evals import evaluators
from src.evals.dataset import load_dataset, push_to_langsmith

log = get_logger("eval")


def _predict(image_path: str) -> dict:
    """Run the extractor + categorizer nodes on one image (no DB writes)."""
    from src.agents.receipt_graph.nodes.categorizer import categorizer_node
    from src.agents.receipt_graph.nodes.extractor import extractor_node
    from src.agents.receipt_graph.nodes.image_encoder import image_encoder_node

    # Minimal reference data so the model has category/payment choices.
    from src.services import expense_service

    categories = {c["category_id"]: c["category_name"] for c in expense_service.list_categories()}
    payment_methods = {
        p["payment_method_id"]: p["payment_method_name"]
        for p in expense_service.list_payment_methods()
    }
    state: dict = {
        "image_path": image_path,
        "categories": categories,
        "payment_methods": payment_methods,
        "model_attempts": 0,
    }
    state.update(image_encoder_node(state))
    state.update(extractor_node(state))
    state.update(categorizer_node(state))
    return state


def run(predict=_predict) -> dict:
    results = []
    for example in load_dataset():
        predicted = predict(example["image_path"])
        score = evaluators.score_extraction(predicted, example["expected"])
        results.append(score)
        log.info("eval.example", accuracy=score["accuracy"], fields=score["fields"])
    metrics = evaluators.aggregate(results)
    log.info("eval.metrics", **metrics)
    return metrics


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--push", action="store_true", help="Push dataset to LangSmith")
    args = parser.parse_args()

    if args.push:
        ds_id = push_to_langsmith()
        log.info("eval.langsmith.pushed", dataset_id=ds_id or "no api key")

    metrics = run()
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
