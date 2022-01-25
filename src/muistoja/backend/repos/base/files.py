import base64
import imghdr
from typing import Any, Tuple, Optional

from fastapi import HTTPException, status

from ....core.config import Config
from ....core.database import Database
from ....core.logging import log


def check_file(compressed_data: str) -> Tuple[Optional[bytes], Optional[str]]:
    try:
        raw_data = base64.b64decode(compressed_data, validate=True)
        file_type = imghdr.what(None, h=raw_data)
        if file_type in Config.files.allowed_filetypes:
            return raw_data, file_type
        else:
            log.info(f'Failed file validation: {file_type}')
    except Exception as e:
        log.exception('Failed file validation', exc_info=e)
    return None, None


class Files:
    """
    Interfacing with files in base64 strings
    """

    def __init__(self, db: Database, user: Any):
        self.db = db
        self.user = user

    async def handle(self, file_data: str) -> int:
        """
        Handle incoming image file data.

        Checks filetype and saves the file.
        Name is generated from Database defaults.

        :param file_data:   data in base64
        :return:            image_id if one was generated
        """
        if file_data is not None and (Config.files.allow_anonymous or self.user.is_authenticated):
            data, file_type = check_file(file_data)
            if data is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Bad image')
            if self.user.is_authenticated:
                m = await self.db.fetch_one(
                    """
                    INSERT INTO images (uploader_id) 
                    SELECT
                        u.id 
                    FROM users u
                        WHERE u.username = :user
                    RETURNING id, file_name
                    """,
                    values=dict(ft=file_type, user=self.user.identity)
                )
            else:
                m = await self.db.fetch_one("INSERT INTO images VALUE () RETURNING id, file_name")
            image_id = m[0]
            file_name = m[1]
            with open(f'{Config.files.location}{file_name}', 'wb') as f:
                f.write(data)
            return image_id


__all__ = ['Files']
