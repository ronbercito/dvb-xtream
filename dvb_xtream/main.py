import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlsplit

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from .config import get_settings
from .db import authenticate, connection, hash_password, initialize

settings = get_settings()
initialize(settings.database_path)
app = FastAPI(title="DVB-Xtream", version="0.1.0")
access_logger = logging.getLogger("dvb_xtream.access")
access_logger.setLevel(logging.INFO)


@app.middleware("http")
async def safe_access_log(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/live/"):
        path = "/live/<credentials>/<stream>"
    elif path == "/player_api.php":
        path = f"{path} action={request.query_params.get('action') or 'login'}"
    elif path == "/get.php":
        path = "/get.php playlist"
    access_logger.info("%s %s %d", request.method, path, response.status_code)
    return response

# Tracks active playback requests for the lifetime of this process. Production
# deployment initially uses one worker so all requests share this registry.
active_streams: dict[str, set[str]] = {}
stream_lock = asyncio.Lock()


class UserInput(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=256)
    expires_at: datetime | None = None
    max_connections: int = Field(default=1, ge=1, le=100)
    enabled: bool = True


class ChannelInput(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    tvh_uuid: str = Field(min_length=1, max_length=128)
    category: str = Field(default="General", max_length=128)
    enabled: bool = True


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Admin key inválida o no configurada")


def client_user(username: str, password: str):
    user = authenticate(settings.database_path, username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas, cuenta vencida o deshabilitada")
    return user


def user_info(user: Any) -> dict[str, Any]:
    expires = user["expires_at"]
    exp_ts = int(datetime.fromisoformat(expires).timestamp()) if expires else 0
    return {
        "username": user["username"], "password": "", "message": "OK", "auth": 1,
        "status": "Active", "exp_date": str(exp_ts), "is_trial": "0",
        "active_cons": str(len(active_streams.get(user["username"], set()))),
        "created_at": "", "max_connections": str(user["max_connections"]),
        "allowed_output_formats": ["ts", "m3u8"],
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "dvb-xtream"}


@app.get("/player_api.php")
def player_api(username: str, password: str, action: str | None = None, category_id: str | None = None):
    user = client_user(username, password)
    with connection(settings.database_path) as db:
        channels = db.execute("SELECT * FROM channels WHERE enabled = 1 ORDER BY category, name").fetchall()
    categories = sorted({row["category"] for row in channels})
    category_list = [{"category_id": str(i + 1), "category_name": name, "parent_id": 0} for i, name in enumerate(categories)]
    streams = [{"num": i + 1, "name": row["name"], "stream_type": "live", "stream_id": row["id"], "stream_icon": "", "epg_channel_id": "", "added": "0", "category_id": str(categories.index(row["category"]) + 1), "custom_sid": "", "tv_archive": 0, "direct_source": "", "tv_archive_duration": "0"} for i, row in enumerate(channels)]
    if action == "get_live_categories":
        return category_list
    if action == "get_live_streams":
        return [stream for stream in streams if category_id is None or stream["category_id"] == category_id]
    if action:
        return []
    public_address = urlsplit(settings.public_url)
    protocol = public_address.scheme or "http"
    server_port = public_address.port or (443 if protocol == "https" else 80)
    return {
        "user_info": user_info(user),
        "server_info": {"url": public_address.hostname or public_address.netloc or settings.public_url, "port": str(server_port), "https_port": str(server_port if protocol == "https" else 443), "server_protocol": protocol, "timezone": "UTC", "timestamp_now": int(datetime.now(timezone.utc).timestamp()), "time_now": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")},
        "available_channels": len(channels),
        "live_categories": category_list,
        "live_streams": streams,
    }


@app.get("/get.php")
def playlist(username: str, password: str, output: str = "ts"):
    client_user(username, password)
    if output not in {"ts", "m3u8", "m3u_plus"}:
        raise HTTPException(status_code=400, detail="Formato no soportado")
    with connection(settings.database_path) as db:
        channels = db.execute("SELECT * FROM channels WHERE enabled = 1 ORDER BY category, name").fetchall()
    lines = ["#EXTM3U"]
    for row in channels:
        lines.extend([f'#EXTINF:-1 tvg-id="{row["id"]}" group-title="{row["category"]}",{row["name"]}', f'{settings.public_url}/live/{quote(username)}/{quote(password)}/{row["id"]}.{output}'])
    return PlainTextResponse("\n".join(lines) + "\n", media_type="audio/x-mpegurl")


@app.get("/live/{username}/{password}/{stream_id}.{extension}")
async def live_stream(username: str, password: str, stream_id: int, extension: str, request: Request):
    user = client_user(username, password)
    if extension not in {"ts", "m3u8"}:
        raise HTTPException(status_code=404, detail="Formato no soportado")
    with connection(settings.database_path) as db:
        channel = db.execute("SELECT * FROM channels WHERE id = ? AND enabled = 1", (stream_id,)).fetchone()
    if not channel:
        raise HTTPException(status_code=404, detail="Canal no encontrado")

    session_id = f"{id(request)}"
    async with stream_lock:
        sessions = active_streams.setdefault(username, set())
        if len(sessions) >= user["max_connections"]:
            raise HTTPException(status_code=429, detail="Límite de conexiones simultáneas alcanzado")
        sessions.add(session_id)

    url = f"{settings.tvh_base_url}/stream/channel/{quote(channel['tvh_uuid'], safe='')}"
    auth = (settings.tvh_username, settings.tvh_password) if settings.tvh_username else None
    upstream_client = httpx.AsyncClient(timeout=None, follow_redirects=True)
    try:
        params = {"profile": settings.tvh_stream_profile} if settings.tvh_stream_profile else None
        upstream_request = upstream_client.build_request("GET", url, params=params, auth=auth)
        upstream_response = await upstream_client.send(upstream_request, stream=True)
        if upstream_response.status_code >= 400:
            upstream_response.raise_for_status()
    except Exception:
        async with stream_lock:
            active_streams.get(username, set()).discard(session_id)
        await upstream_client.aclose()
        raise

    async def relay():
        try:
            async for chunk in upstream_response.aiter_bytes(64 * 1024):
                if await request.is_disconnected():
                    break
                yield chunk
        finally:
            await upstream_response.aclose()
            await upstream_client.aclose()
            async with stream_lock:
                current = active_streams.get(username)
                if current:
                    current.discard(session_id)
                    if not current:
                        active_streams.pop(username, None)

    return StreamingResponse(relay(), media_type="video/mp2t", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@app.post("/admin/users", dependencies=[Depends(require_admin)])
def create_user(payload: UserInput):
    expires = payload.expires_at
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    try:
        with connection(settings.database_path) as db:
            db.execute("INSERT INTO users(username,password_hash,expires_at,max_connections,enabled,created_at) VALUES(?,?,?,?,?,?)", (payload.username, hash_password(payload.password), expires.isoformat() if expires else None, payload.max_connections, int(payload.enabled), datetime.now(timezone.utc).isoformat()))
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise HTTPException(status_code=409, detail="Ese usuario ya existe") from exc
        raise
    return {"username": payload.username, "created": True}


@app.get("/admin/users", dependencies=[Depends(require_admin)])
def list_users():
    with connection(settings.database_path) as db:
        rows = db.execute("SELECT id,username,expires_at,max_connections,enabled,created_at FROM users ORDER BY username").fetchall()
    return [dict(row) for row in rows]


@app.post("/admin/channels", dependencies=[Depends(require_admin)])
def create_channel(payload: ChannelInput):
    try:
        with connection(settings.database_path) as db:
            cursor = db.execute("INSERT INTO channels(name,tvh_uuid,category,enabled) VALUES(?,?,?,?)", (payload.name, payload.tvh_uuid, payload.category, int(payload.enabled)))
            channel_id = cursor.lastrowid
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise HTTPException(status_code=409, detail="Ese UUID de Tvheadend ya está asociado") from exc
        raise
    return {"id": channel_id, "created": True}


@app.get("/admin/channels", dependencies=[Depends(require_admin)])
def list_channels():
    with connection(settings.database_path) as db:
        rows = db.execute("SELECT * FROM channels ORDER BY category,name").fetchall()
    return [dict(row) for row in rows]


@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return HTMLResponse(open(__file__.replace("main.py", "admin.html"), encoding="utf-8").read())


@app.exception_handler(httpx.HTTPError)
async def upstream_error_handler(_request: Request, exc: httpx.HTTPError):
    return JSONResponse(status_code=502, content={"detail": f"No se pudo conectar con Tvheadend: {type(exc).__name__}"})

