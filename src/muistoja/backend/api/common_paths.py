from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Common"])


@router.get(
    "/",
    description=(
            """
            This path is for ensuring the API works.
            """
    ),
    response_class=HTMLResponse
)
def entry(request: Request):
    from textwrap import dedent
    return dedent(
        f"""
        <!DOCTYPE html>
        <html lang="en">
            <meta charset="utf-8"/>
            <link rel="icon" href="{request.url_for('get_image', image='favicon.ico')}"/>
        </html>
        """
    )
