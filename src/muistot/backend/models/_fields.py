from pydantic import constr, conint, confloat, Field

IMAGE_TXT = "Image file name to be fetched from the image endpoint."
IMAGE_NEW = "Image data in base64."
IMAGE = constr(strict=True, strip_whitespace=True, min_length=1)

__ID_REGEX = r"^[a-zA-Z0-9-_]+$"
"""Common regex for project and site ID types
"""
__ID_TYPE_STR = constr(
    strip_whitespace=True, min_length=4, max_length=250, regex=__ID_REGEX
)
"""Common Base for String ID types

Notes
-----
This is applied to project and site ID's
"""
__ID_TYPE_INT = conint(gt=0)

UID = constr(
    strip_whitespace=True, min_length=4, max_length=64, regex=r"^[a-zA-Z0-9-_@.: #äöåÄÖÅ]+$"
)
"""User ID used in the application

Notes
-----
Constrained to be between **4-64** characters
with only **alphabets + -_@.:# and space** allowed.
"""

PID = __ID_TYPE_STR
SID = __ID_TYPE_STR
MID = __ID_TYPE_INT
CID = __ID_TYPE_INT

LANG = constr(min_length=2, max_length=3, regex=r"^[a-z]{2,3}$")
"""Language tag

Notes
-----
This abides ISO 639-1
"""
LANG_FIELD = Field(description="Language tag, supports ISO 639-1 format")

COUNTRY = constr(
    min_length=2,
    max_length=3,
    regex=r"^[a-zA-Z]{2,3}$",
)
"""Country tag

Notes
-----
Supports ISO3166-1 and ISO3316-3
"""
COUNTRY_FIELD = Field(
    description="Country code of the selected country, supports ISO3166-1 and ISO3316-3. Always returns v.3 or empty."
)

LAT = confloat(ge=-90, le=90)
LON = confloat(ge=-180, le=180)

NAME = constr(strip_whitespace=True, min_length=0, max_length=200)
TEXT = constr(strip_whitespace=True, min_length=0, max_length=20_000)
SMALL_TEXT = constr(strip_whitespace=True, min_length=0, max_length=2_500)
LONG_TEXT = constr(strip_whitespace=True, min_length=0, max_length=100_000)


def validate_language(lang: str) -> str:
    from pycountry import languages
    try:
        if len(lang) == 3:
            return languages.get(alpha_3=lang).alpha_2
        else:
            return languages.get(alpha_2=lang).alpha_2
    except (AttributeError, LookupError):
        raise ValueError("No ISO639-1 ID Found")
