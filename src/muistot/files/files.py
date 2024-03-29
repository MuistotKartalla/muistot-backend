import base64
import binascii
import re
from collections import namedtuple
from functools import lru_cache
from pathlib import Path
from typing import Any, Tuple, Optional

from fastapi import HTTPException, status

from ..config import Config
from ..database import Database
from ..logging import log

PREFIX = re.compile(r"^data:image/[a-z]+;base64,")
MIME_PREFIX = re.compile(r"^.+?/")


def is_allowed(file_type: str):
    return file_type in Config.files.allowed_filetypes


def check_file(input_data: str) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Input data in Base64 with optional mime prefix
    """
    file_type = "None"
    try:
        import magic
        input_data = re.sub(PREFIX, "", input_data[:100], count=1) + input_data[100:]
        raw_data = base64.b64decode(input_data, validate=True)
        file_type: str = magic.Magic(mime=True).from_buffer(raw_data)
        if is_allowed(file_type):
            return raw_data, re.sub(MIME_PREFIX, "", file_type)
    except (binascii.Error, UnicodeEncodeError):
        pass
    except Exception as e:
        log.exception(
            f"Exception in file validation\n{file_type}\n{repr(input_data)}",
            exc_info=e,
        )
    return None, None


class Files:
    """
    Interfacing with files in base64 strings
    """
    PATH = re.compile(r"^[a-zA-Z0-9_-]{1,36}(?:\.[a-zA-Z0-9]{1,10})?$")

    def __init__(self, db: Database, user: Any):
        self.db = db
        self.user = user

    async def handle(self, file_data: Optional[str]) -> int:
        """
        Handle incoming image file data.

        Checks filetype and saves the file.
        Name is generated from Database defaults.

        :param file_data:   data in base64
        :return:            image_id if one was generated
        """
        if file_data is not None and self.user.is_authenticated:
            data, file_type = check_file(file_data)
            if data is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad image")
            m = await self.db.fetch_one(
                """
                INSERT INTO images (uploader_id, file_name) 
                SELECT
                    u.id,
                    CONCAT_WS('.', UUID(), :file_type)
                FROM users u
                    WHERE u.username = :user
                RETURNING id, file_name
                """,
                values=dict(user=self.user.identity, file_type=file_type),
            )
            if m is None:
                log.warning(f"Failure to insert file\n{self.user.identity}")
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
            image_id = m[0]
            file_name = m[1]
            with open(self.path(file_name), "wb") as f:
                f.write(data)
            return image_id

    @staticmethod
    def get_mime(file: Path):
        """
        raises FileNotFoundError
        """
        import magic

        return magic.Magic(mime=True).from_file(file)

    @staticmethod
    def path(image: str):
        if not Files.PATH.fullmatch(image):
            raise ValueError("Bad Path")
        else:
            return Config.files.location / image

    Image = namedtuple("Image", ("exists", "path", "mime"))

    class Images:
        DEFAULT = "placeholder.jpg"
        SYSTEM_IMAGES = {DEFAULT, "favicon.ico"}

        @staticmethod
        @lru_cache(maxsize=64)
        def get(item: str) -> 'Files.Image':
            """Careful with the path this is sensitive to injection if not sanitized
            """
            import os
            path = Files.path(item)
            if item in Files.Images.SYSTEM_IMAGES or os.path.exists(path):
                return Files.Image(exists=True, path=path, mime=Files.get_mime(path))
            else:
                return Files.Image(exists=False, path=None, mime=None)


__all__ = ["Files"]
