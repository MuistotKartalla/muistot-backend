from textwrap import dedent
from typing import List, Type

from pydantic import BaseModel, create_model, BaseConfig

from .comment import Comment
from .memory import Memory
from .project import Project
from .site import Site


def make_collection(model_cls: Type[BaseModel]):
    type_name = model_cls.__name__ + "Collection"

    class Config(BaseConfig):
        pass

    collection_model = create_model(
        type_name, __config__=Config, items=(List[model_cls], None)
    )

    collection_model.__doc__ = f"{model_cls.__name__} Collection"

    return collection_model


Projects = make_collection(Project)
Sites = make_collection(Site)
Memories = make_collection(Memory)
Comments = make_collection(Comment)

Comments.Config.__examples__ = {
    "normal": dict(
        map(
            lambda e: e if e[0] != "value" else ("value", {"items": [e[1]]}),
            Comment.Config.__examples__["normal"].items(),
        )
    ),
    "own": dict(
        map(
            lambda e: e
            if e[0] != "value"
            else (
                "value",
                {"items": [e[1], Comment.Config.__examples__["normal"]["value"]]},
            ),
            Comment.Config.__examples__["own"].items(),
        )
    ),
}

Projects.Config.__examples__ = {
    "missing": {
        "summary": "Differing Locale",
        "value": {
            "items": [
                Project.Config.__examples__["basic"]["value"],
                {
                    "id": "missing-locale",
                    "site_count": 7,
                    "info": {"lang": "se", "name": "Hejsan"},
                    "admin_posting": True,
                },
            ]
        },
        "description": dedent(
            """
            The _Locale_ (lang) is not guaranteed to be the same for all projects returned.
            Best effort is made to return projects with info locale matching the `Accept-Language` header,
            but any project that is missing the selected locale will be returned with the default locale instead.

            However, the locale object will never be missing. Any projects without a default info will be rejected.
            """
        ),
    },
    "sample": {
        "summary": "Collection of Projects",
        "value": {
            "items": [
                Project.Config.__examples__["basic"]["value"],
                dict(
                    map(
                        lambda e: e if e[0] != "id" else (e[0], e[1] + "-copy"),
                        Project.Config.__examples__["basic"]["value"].items(),
                    )
                ),
            ]
        },
        "description": "All values will have a _unique_ id.",
    },
}
