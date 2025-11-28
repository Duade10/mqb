from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)
cors_origins = settings.cors_allow_origins or (
    [settings.public_frontend_base_url]
    if settings.public_frontend_base_url
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=settings.cors_allow_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/", tags=["Public"])
def root() -> dict[str, str]:
    return {"message": "mrhost guest qr backend"}
