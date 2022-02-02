from fastapi.responses import FileResponse

from .common_imports import *
from ..repos.base.files import get_mime
from ...core.config import Config

router = make_router(tags=["Files"])
DEFAULT = 'placeholder.jpg'
SYSTEM_IMAGES = {DEFAULT, 'favicon.ico'}


def path(image: str):
    return f'{Config.files.location}{image}'


@router.get(
    "/images/{image}",
    description=(
            """
            Return's an image from the uploads folder.
            """
    )
)
async def get_image(image: str, db: Database = Depends(dba)):
    if image in SYSTEM_IMAGES:
        file_name = image
    else:
        file_name = await db.fetch_val(
            'SELECT file_name FROM images WHERE file_name = :name',
            values=dict(name=image)
        ) or DEFAULT
    try:
        file = path(file_name)
        return FileResponse(path=file, media_type=get_mime(file))
    except FileNotFoundError:
        try:
            file = path(DEFAULT)
            return FileResponse(path=file, media_type=get_mime(file))
        except FileNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='File not found')
