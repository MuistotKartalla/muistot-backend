from textwrap import dedent

from fastapi import Path, status
from fastapi.responses import FileResponse, Response
from headers import LOCATION

from .utils import make_router
from ..repos import Files

router = make_router(tags=["Files"])


@router.get(
    "/images/{image}",
    description=dedent(
        """
        Returns an image that is publicly available or uploaded by a user.
        
        The image names are available from their parent entities and the actual image is available from here.
        """
    ),
    response_class=FileResponse,
    status_code=200,
    responses={
        303: {
            "description": dedent(
                """
                The requested file was not found or is unavailable.
                
                The request Location header will contain a path to the default image.
                """
            ),
            "headers": {
                LOCATION: {"description": "Path to default resource", "type": "string"}
            },
        },
        422: {
            "description": "The path parameter was invalid",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": 422,
                            "message": "request validation error",
                            "errors": [
                                {
                                    "loc": ["path", "image"],
                                    "msg": "string does not match regex ...",
                                    "type": "value_error.str.regex",
                                }
                            ],
                        }
                    }
                }
            },
        },
    },
)
async def get_image(image: str = Path(..., regex=Files.PATH.pattern)):
    image = Files.Images.get(image)
    if not image.exists:
        return Response(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={LOCATION: router.url_path_for("get_image", image=Files.Images.DEFAULT)},
        )
    else:
        return FileResponse(path=image.path, media_type=image.mime)
