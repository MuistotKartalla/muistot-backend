from fastapi.responses import FileResponse

from .common_imports import *

router = make_router(tags=["Files"])


@router.get("/images/{image}")
async def get_image(image: str, db: Database = Depends(dba)):
    exists = await db.fetch_val(
        'SELECT EXISTS(SELECT 1 FROM images WHERE file_name = :name)',
        values=dict(name=image)
    ) == 1
    if exists:
        try:
            from ..config import Config
            import imghdr
            file = Config.files.location + image
            ft = imghdr.what(file)
            return FileResponse(path=file, media_type=f'image/{ft}')
        except FileNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='File not found')
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='File not found')
