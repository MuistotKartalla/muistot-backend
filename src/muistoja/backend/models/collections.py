from typing import List, Type

from pydantic import BaseModel, create_model, BaseConfig

from .comment import Comment
from .memory import Memory
from .project import Project
from .site import Site


def make_collection(model_cls: Type[BaseModel]):
    type_name = model_cls.__name__ + 'Collection'

    class Config(BaseConfig):
        pass

    collection_model = create_model(
        type_name,
        __config__=Config,
        items=(List[model_cls], None)
    )

    collection_model.__doc__ = f"{model_cls.__name__} Collection"

    return collection_model


Projects = make_collection(Project)
Sites = make_collection(Site)
Memories = make_collection(Memory)
Comments = make_collection(Comment)

Comments.Config.__examples__ = {
    "normal": map(
        lambda e: e if e[0] != "value" else ("value", {"items": [e[1]]}),
        Comment.Config.__examples__['normal'].items()
    ),
    "own": map(
        lambda e: e if e[0] != "value" else (
            "value",
            {
                "items": [
                    e[1],
                    Comment.Config.__examples__['normal']['value']
                ]
            }
        ),
        Comment.Config.__examples__['own'].items()
    )
}
