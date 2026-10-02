import json, logging, time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .controllers import analytics_controller, auth_controller, episode_controller, request_controller
from .db import migrate
from .errors import DomainError

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("api")

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_):
    migrate()
    index = FRONTEND / "index.html"
    if index.is_file():
        log.info(json.dumps({"ui": f"serving {FRONTEND}"}))
    else:  # the usual cause of a bare {"detail":"Not Found"} at "/"
        log.warning(json.dumps({"warning": f"UI missing: {index} does not exist"}))
    yield


app = FastAPI(title="Dataset Request Desk", lifespan=lifespan)


@app.exception_handler(DomainError)
async def domain_error(_, e: DomainError):
    return JSONResponse({"detail": e.msg}, status_code=e.status)


@app.middleware("http")
async def access_log(req: Request, call_next):
    t, status = time.perf_counter(), 500
    try:
        resp = await call_next(req)
        status = resp.status_code
        resp.headers.setdefault("Cache-Control", "no-cache")  # always revalidate UI files and API data
        return resp
    finally:
        log.info(json.dumps({"method": req.method, "path": req.url.path, "status": status,
                             "ms": round((time.perf_counter() - t) * 1000, 1),
                             "user_id": getattr(req.state, "uid", None)}))


for router in (auth_controller.router, request_controller.router,
               episode_controller.router, analytics_controller.router):
    app.include_router(router)

# Must stay last: a mount at "/" matches everything the API routes above didn't.
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="ui")
