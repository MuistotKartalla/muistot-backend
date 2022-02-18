from fastapi import APIRouter

from .admin import router as admin_router
from .comments import router as comment_router
from .common import router as common_paths
from .files import router as file_router
from .me import router as me_router
from .memories import router as memory_router
from .projects import router as project_router
from .sites import router as site_router

router = APIRouter()
router.include_router(project_router)
router.include_router(site_router)
router.include_router(memory_router)
router.include_router(comment_router)
router.include_router(file_router)
router.include_router(admin_router)
router.include_router(me_router)
api_paths = router

__all__ = [
    'common_paths',
    'api_paths'
]
