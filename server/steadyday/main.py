from contextlib import asynccontextmanager
from datetime import date
import re
import secrets
from typing import Any, Literal
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .db import Database, StoreUnavailable
from .models import CheckIn, GoalUpdate, Goals, HabitCompletion, HabitUpdate, Onboard, ProfileUpdate, Reminder, TitledItem
from .service import AppError, DemoService, utcnow

COOKIE = "steadyday_demo"
TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")
BODY_LIMIT = 2048
CHECKIN_BODY_LIMIT = 8192
WRITE_METHODS = {"POST", "PUT", "DELETE"}
SITE_ROUTES = ("/", "/demo", "/privacy", "/check-in", "/insights", "/goals-habits", "/coach", "/settings")


def error(status: int, code: str, message: str, fields: list[str] | None = None) -> JSONResponse:
    value: dict[str, Any] = {"code": code, "message": message}
    if fields:
        value["fields"] = fields
    return JSONResponse({"error": value}, status_code=status, headers={"Cache-Control": "no-store"})


def is_local_route(request: Request) -> bool:
    return request.url.path.startswith("/api/demo/")


def local_origin(request: Request, config: Settings) -> str:
    if config.app_origin:
        return config.app_origin
    host = request.url.hostname
    if host in {"127.0.0.1", "localhost", "testserver", "::1"}:
        return f"{request.url.scheme}://{request.url.netloc}"
    raise AppError(403, "ORIGIN", "Use the configured demo origin.")


def create_app(settings: Settings | None = None, clock=utcnow) -> FastAPI:
    cfg = settings or Settings.from_env()
    db = Database(cfg.database_url)
    demo = DemoService(cfg, db, clock)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            try:
                db.init()
            except StoreUnavailable:
                raise RuntimeError("Database initialization failed. Check the connection and schema permissions.") from None
            yield
        finally:
            db.dispose()

    app = FastAPI(title="SteadyDay Demo API", version="1.0.0", lifespan=lifespan,
                  docs_url="/docs" if cfg.mode == "local" else None,
                  redoc_url=None, openapi_url="/openapi.json" if cfg.mode == "local" else None)
    app.state.db = db
    app.state.demo = demo

    @app.exception_handler(AppError)
    async def application_error(_: Request, exc: AppError):
        return error(exc.status, exc.code, exc.message)

    @app.exception_handler(StoreUnavailable)
    async def database_error(_: Request, __: StoreUnavailable):
        return error(503, "BACKEND_UNAVAILABLE", "The demo service is temporarily unavailable.")

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        # Exclude values, and never reflect arbitrary keys supplied by clients.
        allowed = {"persona", "consent", "access_code", "sleep_minutes", "activity_minutes",
                   "energy", "activity_days", "checkin_days", "time", "day", "habit", "completed",
                   "mood", "stress", "hydration", "notes", "days", "id", "title", "name", "language", "theme",
                   "reminder_enabled", "notifications_enabled"}
        keys = sorted({str(e["loc"][-1]) for e in exc.errors() if e.get("loc") and e["loc"][-1] in allowed})
        return error(422, "VALIDATION_ERROR", "Review the values entered and try again.", keys)

    @app.middleware("http")
    async def boundary(req: Request, call_next):
        api = req.url.path.startswith(("/v1/", "/api/demo/"))
        if api and req.method in {"POST", "PUT"}:
            raw_length = req.headers.get("content-length", "")
            if not raw_length.isascii() or not raw_length.isdecimal() or len(raw_length) > 6:
                return error(411, "LENGTH_REQUIRED", "Send a short JSON request.")
            body_limit = CHECKIN_BODY_LIMIT if req.url.path in {"/api/demo/check-in", "/v1/check-in"} else BODY_LIMIT
            if not 1 <= int(raw_length) <= body_limit:
                return error(413, "PAYLOAD_LIMIT", "The demo request is too large or empty.")
            if req.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
                return error(415, "CONTENT_TYPE", "Send JSON.")
        response = await call_next(req)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if api:
            response.headers["Cache-Control"] = "no-store"
        if req.url.path in SITE_ROUTES:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
            )
        return response

    def gate(req: Request) -> None:
        if is_local_route(req):
            if req.method in WRITE_METHODS:
                expected = local_origin(req, cfg)
                if not secrets.compare_digest(req.headers.get("origin", "").encode(), expected.encode()):
                    raise AppError(403, "ORIGIN", "Open the demo directly to make changes.")
        elif cfg.proxy_key and not secrets.compare_digest(req.headers.get("x-proxy-key", "").encode(), cfg.proxy_key.encode()):
            raise AppError(403, "PROXY_REQUIRED", "Use the authorised demo application.")

    def token(req: Request) -> str:
        if is_local_route(req):
            value = req.cookies.get(COOKIE, "")
        else:
            auth = req.headers.get("authorization", "")
            value = auth[7:] if auth.startswith("Bearer ") else ""
        if not TOKEN.fullmatch(value):
            raise AppError(401, "SESSION_REQUIRED", "Start a new demo or resume an active one.")
        return value

    def current(req: Request) -> dict[str, Any]:
        return demo.get(token(req))

    @app.get("/healthz")
    @app.get("/api/health")
    def health():
        if not db.healthy():
            return error(503, "BACKEND_UNAVAILABLE", "The database is not ready.")
        return {"status": "ok"}

    router = APIRouter(dependencies=[Depends(gate)])

    @router.get("/config")
    def demo_config():
        return {"requires_access_code": bool(cfg.access_code), "session_days": cfg.session_days,
                "timezone": cfg.timezone, "synthetic_only": True}

    @router.post("/session", status_code=201)
    def session_create(req: Request, data: Onboard):
        if is_local_route(req) and req.cookies.get(COOKIE):
            try:
                current(req)
            except AppError as exc:
                if exc.status != 401:
                    raise
            else:
                raise AppError(409, "SESSION_EXISTS", "Continue your existing demo or delete it first.")
        raw, ttl = demo.create(data)
        if not is_local_route(req):
            return {"session_token": raw, "expires_in": ttl}
        out = JSONResponse({"created": True}, status_code=201)
        out.set_cookie(COOKIE, raw, max_age=ttl, httponly=True, samesite="strict",
                       secure=urlsplit(local_origin(req, cfg)).scheme == "https", path="/")
        return out

    @router.get("/dashboard")
    def dashboard(session=Depends(current)):
        return demo.dashboard(session)

    @router.get("/insights")
    def insights(days: Literal["week", "7", "14", "30"] = "14", session=Depends(current)):
        return demo.insights(session, days)

    @router.get("/profile")
    def profile(session=Depends(current)):
        return demo.profile(session)

    @router.put("/profile")
    def update_profile(data: ProfileUpdate, session=Depends(current)):
        return demo.update_profile(session, data)

    @router.get("/check-in")
    def get_checkin(day: date | None = None, session=Depends(current)):
        return {"entry": demo.get_checkin(session, day)}

    @router.put("/check-in")
    def checkin(data: CheckIn, session=Depends(current)):
        return demo.checkin(session, data)

    @router.delete("/check-in")
    def delete_checkin(day: date, session=Depends(current)):
        return demo.delete_checkin(session, day)

    @router.put("/goals")
    def goals(data: Goals, session=Depends(current)):
        return demo.goals(session, data)

    @router.get("/goals")
    def list_goals(session=Depends(current)):
        return {"goals": demo.list_goals(session)}

    @router.post("/goal", status_code=201)
    def create_goal(data: TitledItem, session=Depends(current)):
        return demo.create_goal(session, data.title)

    @router.put("/goal")
    def update_goal(data: GoalUpdate, session=Depends(current)):
        return demo.update_goal(session, data)

    @router.delete("/goal")
    def delete_goal(id: UUID, session=Depends(current)):
        return demo.delete_goal(session, str(id))

    @router.put("/habits")
    def habit(data: HabitCompletion, session=Depends(current)):
        return demo.habit(session, data)

    @router.get("/habits")
    def list_habits(session=Depends(current)):
        return {"custom_habits": demo.list_habits(session)}

    @router.post("/habit", status_code=201)
    def create_habit(data: TitledItem, session=Depends(current)):
        return demo.create_habit(session, data.title)

    @router.put("/habit")
    def update_habit(data: HabitUpdate, session=Depends(current)):
        return demo.update_habit(session, data)

    @router.delete("/habit")
    def delete_habit(id: UUID, session=Depends(current)):
        return demo.delete_habit(session, str(id))

    @router.put("/reminder")
    def reminder(data: Reminder, session=Depends(current)):
        return demo.reminder(session, data)

    @router.get("/export")
    def export(session=Depends(current)):
        data = demo.export(session)
        return JSONResponse(data, headers={"Content-Disposition": 'attachment; filename="steadyday-demo.json"'})

    @router.delete("/session")
    def session_delete(req: Request, session=Depends(current)):
        demo.delete(session)
        out = JSONResponse({"deleted": True})
        if is_local_route(req):
            out.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict",
                              secure=urlsplit(local_origin(req, cfg)).scheme == "https")
        return out

    app.include_router(router, prefix="/v1")
    if cfg.mode == "local":
        app.include_router(router, prefix="/api/demo")

        def site():
            return FileResponse(cfg.assets / "index.html", headers={"Cache-Control": "no-cache"})

        for path in SITE_ROUTES:
            app.add_api_route(path, site, methods=["GET"], include_in_schema=False)

        app.mount("/steadyday", StaticFiles(directory=cfg.assets, check_dir=False), name="assets")
    return app


app = create_app()
