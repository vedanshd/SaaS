from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, dashboard, stripe, admin

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(stripe.router, prefix="/stripe", tags=["stripe"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])