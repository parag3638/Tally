"""Insights narrator: turns detected anomalies + summary stats into a concise,
grounded natural-language brief. The model is instructed to use ONLY the numbers
provided (the detectors already computed them) — it must not invent figures.
"""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.models import plain_model

_SYSTEM = (
    "You are a financial insights assistant. You are given pre-computed anomalies "
    "and monthly spending summaries as JSON. Write a short, friendly brief (3-6 "
    "sentences) highlighting the most important findings and one practical "
    "suggestion. Use ONLY the numbers provided — never invent or estimate figures. "
    "If there are no anomalies, say spending looks normal and give a brief summary."
)


def generate_brief(anomalies: list[dict], summary: list[dict]) -> str:
    payload = json.dumps({"anomalies": anomalies, "monthly_summary": summary}, default=str)
    model = plain_model("insights")
    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=f"Here is the data:\n{payload}\n\nWrite the brief."),
    ]
    return model.invoke(messages).content
