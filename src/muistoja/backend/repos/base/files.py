import base64
import re
from typing import Any, Tuple, Optional

from fastapi import HTTPException, status

from ....core.config import Config
from ....core.database import Database
from ....core.logging import log

PREFIX = re.compile(r'^data:image/[a-z]+;base64,')
MIME_PREFIX = re.compile(f'^.+?/')


def check_file(compressed_data: str) -> Tuple[Optional[bytes], Optional[str]]:
    file_type = 'None'
    try:
        import magic
        compressed_data = re.sub(PREFIX, '', compressed_data[:100], count=1) + compressed_data[100:]
        raw_data = base64.b64decode(compressed_data, validate=True)
        file_type: str = magic.Magic(mime=True).from_buffer(raw_data)
        if file_type in Config.files.allowed_filetypes:
            return raw_data, re.sub(MIME_PREFIX, '', file_type)
        else:
            log.info(f'Failed file validation\n{file_type}\n{[hex(b) for b in raw_data[:12]]}')
    except Exception as e:
        log.exception(f'Exception in file validation\n{file_type}\n{compressed_data[:40]}', exc_info=e)
    return None, None


def get_mime(file: str):
    """
    raises FileNotFoundError
    """
    import magic
    return magic.Magic(mime=True).from_file(file)


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
                    values=dict(user=self.user.identity)
                )
            else:
                m = await self.db.fetch_one("INSERT INTO images VALUE () RETURNING id, file_name")
            if m is None:
                log.warning(f'Failure to insert file\n{self.user.identity}')
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
            image_id = m[0]
            file_name = m[1]
            with open(f'{Config.files.location}{file_name}', 'wb') as f:
                f.write(data)
            return image_id


__all__ = ['Files', 'get_mime']
