from fastapi import APIRouter

from .admin import router as admin_routes
from .comments import router as comment_router
from .common_paths import router as common_paths
from .files import router as file_router
from .memories import router as memory_router
from .projects import router as project_router
from .sites import router as site_router

router = APIRouter()
router.include_router(project_router)
router.include_router(site_router)
router.include_router(memory_router)
router.include_router(comment_router)
router.include_router(file_router)
router.include_router(admin_routes)
api_paths = router

__all__ = ['common_paths', 'api_paths']
