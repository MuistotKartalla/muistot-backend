from typing import Dict

from fastapi import Body
from headers import LOCATION


def sample(model) -> Body:
    return Body(
        ...,
        examples=
        model.Config.__examples__
        if hasattr(model, 'Config') and hasattr(model.Config, '__examples__')
        else None
    )


def sample_response(model, description: str = None) -> Dict:
    out = {}
    if description:
        out["description"] = description
    out["content"] = {
        "application/json": {
            "examples": model.Config.__examples__
        }
    }
    return out


def d(_description: str, **kwargs):
    return {"description": _description, **kwargs}


def h(_h: str, _description: str, _type: str):
    yield _h, {"description": _description, "type": _type}


def loc(_description: str):
    return next(h(LOCATION, _description, "string"))


def get_samples(model):
    if hasattr(model.Config, '__examples__'):
        return sample_response(model)
    else:
        return dict()
