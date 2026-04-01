def score_confidence(base_conf: float, impacts: list) -> float:
    """Aggregates all components' impacts on confidence. Clamps between 0.0 and 1.0."""
    total = base_conf + sum(impacts)
    return max(0.0, min(1.0, round(total, 2)))
