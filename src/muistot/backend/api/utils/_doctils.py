from fastapi import Body


def check_samples(model):
    """Check if model has samples and that they are okay"""
    import re
    samples = model.Config.__examples__
    for k, v in samples.items():
        assert re.match(r"^[a-z]+$", k), f'Unconventional sample name {k}'
        assert "value" in v, f'Missing value {v}'
        assert "summary" in v, f'Missing summary {v}'
    return samples


def sample(model) -> Body:
    """Single sample for input parameter from JSON Body"""
    return Body(
        ...,
        examples=check_samples(model)
        if hasattr(model, "Config") and hasattr(model.Config, "__examples__")
        else None,
    )


def d(_description: str, **kwargs):
    """Adds a description"""
    return {"description": _description, **kwargs}


def get_samples(model):
    """Introspect Model for samples"""
    if hasattr(model.Config, "__examples__"):
        return dict(
            content={
                "application/json":
                    {
                        "examples": check_samples(model)
                    }
            }
        )
    else:
        return dict()
