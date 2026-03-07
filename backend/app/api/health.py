"""Health and auth status endpoints."""

import asyncio
import shutil
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/auth/status")
async def auth_status():
    gws_path = shutil.which("gws")
    if not gws_path:
        return {"gws_installed": False, "gws_authenticated": False, "message": "gws CLI not found. Run: npm install -g @googleworkspace/cli"}

    try:
        proc = await asyncio.create_subprocess_exec(
            "gws", "auth", "status",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        authenticated = proc.returncode == 0
        return {
            "gws_installed": True,
            "gws_authenticated": authenticated,
            "message": stdout.decode().strip() if authenticated else "Not authenticated. Run: gws auth login",
        }
    except asyncio.TimeoutError:
        return {"gws_installed": True, "gws_authenticated": False, "message": "gws auth status timed out"}
    except Exception as e:
        return {"gws_installed": True, "gws_authenticated": False, "message": str(e)}
