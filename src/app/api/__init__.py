from fastapi import APIRouter

from .comments import router as comment_router
from .common_paths import router as common_paths
from .memories import router as memory_router
from .projects import router as project_router
from .sites import router as site_router

router = APIRouter(prefix='/api')
router.include_router(project_router)
router.include_router(site_router)
router.include_router(memory_router)
router.include_router(comment_router)
api_paths = router

__all__ = ['common_paths', 'api_paths']
