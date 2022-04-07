import base64
import binascii
import re
from collections import namedtuple
from functools import lru_cache
from typing import Any, Tuple, Optional

from fastapi import HTTPException, status

from ....config import Config
from ....database import Database
from ....logging import log

PREFIX = re.compile(r"^data:image/[a-z]+;base64,")
MIME_PREFIX = re.compile(r"^.+?/")


def is_allowed(file_type: str):
    return file_type in Config.files.allowed_filetypes


def check_file(compressed_data: str) -> Tuple[Optional[bytes], Optional[str]]:
    file_type = "None"
    try:
        import magic
        compressed_data = re.sub(PREFIX, "", compressed_data[:100], count=1) + compressed_data[100:]
        raw_data = base64.b64decode(compressed_data, validate=True)
        file_type: str = magic.Magic(mime=True).from_buffer(raw_data)
        if is_allowed(file_type):
            return raw_data, re.sub(MIME_PREFIX, "", file_type)
    except (binascii.Error, IndexError):
        pass
    except Exception as e:
        log.exception(
            f"Exception in file validation\n{file_type}\n{compressed_data[:40]}",
            exc_info=e,
        )
    return None, None


class Files:
    """
    Interfacing with files in base64 strings
    """
    PATH = re.compile(r"^[\w-]{1,36}(?:\.[a-zA-Z0-9]{1,10})?$")

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
        if file_data is not None and (
                Config.files.allow_anonymous or self.user.is_authenticated
        ):
            data, file_type = check_file(file_data)
            if data is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad image")
            if self.user.is_authenticated:
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
            else:
                m = await self.db.fetch_one(
                    """
                    INSERT INTO images (file_name)
                    VALUE (CONCAT_WS('.', UUID(), :file_type))
                    RETURNING id, file_name
                    """,
                    values=dict(file_type=file_type)
                )
            if m is None:
                log.warning(f"Failure to insert file\n{self.user.identity}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
            image_id = m[0]
            file_name = m[1]
            with open(self.path(file_name), "wb") as f:
                f.write(data)
            return image_id

    @staticmethod
    def get_mime(file: str):
        """
        raises FileNotFoundError
        """
        import magic

        return magic.Magic(mime=True).from_file(file)

    @staticmethod
    def path(image: str):
        if not Files.PATH.match(image):
            raise ValueError("Bad Path")
        if Config.files.location.endswith("/"):
            return f"{Config.files.location}{image}"
        else:
            return f"{Config.files.location}/{image}"

    Image = namedtuple("Image", ("exists", "path", "mime"))

    class Images:
        DEFAULT = "placeholder.jpg"
        SYSTEM_IMAGES = {DEFAULT, "favicon.ico"}

        @staticmethod
        @lru_cache(maxsize=64)
        def get(item: str) -> 'Files.Image':
            import os
            path = Files.path(item)
            if item in Files.Images.SYSTEM_IMAGES or os.path.exists(path):
                return Files.Image(exists=True, path=path, mime=Files.get_mime(path))
            else:
                return Files.Image(exists=False, path=None, mime=None)


__all__ = ["Files"]
