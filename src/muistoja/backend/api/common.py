import textwrap

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Common"])


@router.get(
    "/",
    description=textwrap.dedent(
        """
        #### This path is for ensuring the API works.
        
        Returns an empty HTML page with `favicon.ico` visible.
        This will tell if the static image endpoint works properly.
        """
    ),
    response_class=HTMLResponse,
)
def entry(request: Request):
    return textwrap.dedent(
        f"""
        <!DOCTYPE html>
        <html lang="en">
            <meta charset="utf-8"/>
            <link rel="icon" href="{request.url_for('get_image', image='favicon.ico')}"/>
        </html>
        """
    )


@router.get(
    "/languages",
    description=textwrap.dedent(
        """
        #### For querying display names for languages
        
        Returns a language entry on query.
        The query supports querying both ISO639-1 and ISO639-3 codes.
        """
    ),
    responses={
        422: {"description": "Invalid language id"},
        404: {"description": "Language not found"},
        400: {"description": "Language has no short code"},
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "ISO639-3 Language ID",
                                "example": "fin",
                            },
                            "name": {
                                "type": "string",
                                "description": "ISO Language Name",
                                "example": "Finnish",
                            },
                        },
                    }
                }
            },
        },
    },
)
def languages(q: str = Query(..., regex=r"^[a-z]{2,3}$")):
    try:
        from pycountry import languages

        lang = languages.lookup(q)
        return {"id": lang.alpha_3, "name": lang.name}
    except (LookupError, AttributeError):
        raise HTTPException(status_code=404, detail="Language not found")
