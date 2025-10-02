from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.include_router(router)


@app.get("/", tags=["Public"])
def root() -> dict[str, str]:
    return {"message": "mrhost guest qr backend"}
