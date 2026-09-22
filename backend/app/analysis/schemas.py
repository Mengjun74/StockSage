"""Response schemas the models are constrained to. Kept beside the prompts because the
two change together."""

CASE_SCHEMA = {
    "type": "object",
    "properties": {
        "case_strength": {"type": "string", "enum": ["strong", "moderate", "weak"]},
        "summary": {"type": "string"},
        "points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "evidence": {"type": "string"},
                },
                "required": ["claim", "evidence"],
            },
        },
        "strongest_counterpoint": {"type": "string"},
    },
    "required": ["case_strength", "summary", "points", "strongest_counterpoint"],
}

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["buy", "accumulate_on_pullback", "hold", "reduce", "avoid"]},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "horizon_days": {"type": "integer"},
        "entry_label": {"type": "string"},
        "target_label": {"type": "string"},
        "stop_label": {"type": "string"},
        "reasoning": {"type": "string"},
        "invalidation": {"type": "string"},
        "disagreement": {"type": "string"},
    },
    "required": [
        "action", "confidence", "horizon_days", "entry_label", "target_label",
        "stop_label", "reasoning", "invalidation", "disagreement",
    ],
}
