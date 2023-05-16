from fastapi import HTTPException
from pycountry import languages
from pydantic import constr, conint, confloat, Field

from ...config import Config

# language=pythonregexp
__ID_REGEX = r"^[a-zA-Z0-9-_]+$"
__ID_TYPE_STR = constr(strip_whitespace=True, min_length=4, max_length=250, regex=__ID_REGEX)
__ID_TYPE_INT = conint(gt=0)

UID = constr(
    strip_whitespace=True,
    min_length=4,
    max_length=64,
    # language=pythonregexp
    regex=r"^[a-zA-Z0-9-_@.: #äöåÄÖÅ]+$",
)
"""
User ID used in the application

Notes
-----
Constrained to be between **4-64** characters
with only **alphabets + -_@.:# and space** allowed.
"""

PID = __ID_TYPE_STR
"""
Project ID

Notes
-----
String type id with common format
"""

SID = __ID_TYPE_STR
"""
Site ID

Notes
-----
String type id with common format
"""

MID = __ID_TYPE_INT
"""
Memory ID

Notes
-----
Integer type id starting from 0
"""

LANG_FIELD = Field(description="Language tag, supports ISO 639-1 format")
LANG = constr(
    min_length=2,
    max_length=3,
    regex=r"^[a-z]{2,3}$",
)
"""
Language tag

Notes
-----
This abides ISO 639-1
"""

COUNTRY_FIELD = Field(description="Country code. Supports ISO3166-1 and ISO3316-3. Always returns v.3 or empty.")
COUNTRY = constr(
    min_length=2,
    max_length=3,
    regex=r"^[a-zA-Z]{2,3}$",
)
"""
Country tag

Notes
-----
Supports ISO3166-1 and ISO3316-3
"""

IMAGE_TXT = "Image file name to be fetched from the image endpoint."
IMAGE_NEW = "Image data in base64."
IMAGE = constr(
    strict=True,
    strip_whitespace=True,
    min_length=1,
)
"""
Image Data

Notes
-----
Contains image data in base64
"""

LAT = confloat(ge=-90, le=90)
LON = confloat(ge=-180, le=180)

NAME = constr(strip_whitespace=True, min_length=0, max_length=200)
TEXT = constr(strip_whitespace=True, min_length=0, max_length=20_000)
SMALL_TEXT = constr(strip_whitespace=True, min_length=0, max_length=2_500)
LONG_TEXT = constr(strip_whitespace=True, min_length=0, max_length=100_000)


def validate_language(lang: str) -> str:
    """
    Image Data

    Raises
    ------
    HTTPException(406) if the language is not supported
    ValueError if there is a failure in parsing the language
    """
    try:
        if len(lang) == 3:
            lang = languages.get(alpha_3=lang).alpha_2
        else:
            lang = languages.get(alpha_2=lang).alpha_2
        if lang not in Config.localization.supported:
            raise HTTPException(status_code=406, detail='Unsupported language')
        return lang
    except (AttributeError, LookupError):
        raise ValueError("No ISO639-1 ID Found")
