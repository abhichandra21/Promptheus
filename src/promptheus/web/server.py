"""FastAPI server for Promptheus Web UI."""
import asyncio
import logging
import webbrowser
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from promptheus.config import Config
from promptheus.providers import get_provider
from promptheus.history import get_history
from promptheus.constants import VERSION, GITHUB_REPO

# Import API routers
from promptheus.web.api.prompt_router import router as prompt_router
from promptheus.web.api.history_router import router as history_router
from promptheus.web.api.providers_router import router as providers_router
from promptheus.web.api.settings_router import router as settings_router
from promptheus.web.api.questions_router import router as questions_router

# Create FastAPI app
app = FastAPI(title="Promptheus Web API", version="1.0.0")

# Add CORS middleware (only allow localhost origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:*", "http://localhost:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers first (before static files to avoid conflicts)
app.include_router(prompt_router, prefix="/api")
app.include_router(history_router, prefix="/api")
app.include_router(providers_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(questions_router, prefix="/api")


@app.get("/api/version")
async def get_version():
    """Get version information including development build details."""
    import os
    import subprocess
    from datetime import datetime

    # Get git commit info if available
    commit_hash = None
    commit_date = None
    is_dirty = False

    try:
        # Get current commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).parent.parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            commit_hash = result.stdout.strip()[:8]  # Short hash

            # Check if working directory is dirty
            diff_result = subprocess.run(
                ["git", "diff", "--quiet"],
                cwd=Path(__file__).parent.parent.parent.parent,
                capture_output=True,
                timeout=5
            )
            is_dirty = diff_result.returncode != 0

            # Get commit date
            date_result = subprocess.run(
                ["git", "log", "-1", "--format=%ci", "HEAD"],
                cwd=Path(__file__).parent.parent.parent.parent,
                capture_output=True,
                text=True,
                timeout=5
            )
            if date_result.returncode == 0:
                commit_date = date_result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        pass

    return {
        "version": VERSION,
        "full_version": f"v{VERSION}",
        "commit_hash": commit_hash,
        "commit_date": commit_date,
        "is_dirty": is_dirty,
        "build_type": "dev" if is_dirty else "clean",
        "github_repo": GITHUB_REPO,
        "timestamp": datetime.now().isoformat()
    }


# Static files for SPA - must be after API routes
spa_dir = Path(__file__).parent / "static"
assets_dir = Path(__file__).parent.parent.parent.parent / "assets"

# Serve index.html for root
NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


@app.get("/")
async def read_root():
    index_path = spa_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path, headers=NO_CACHE_HEADERS)
    return {"message": "Promptheus Web API is running"}

# Serve assets (images, etc.)
@app.get("/assets/{file_path:path}")
async def serve_assets(file_path: str):
    """Serve assets from the assets directory."""
    asset_file = assets_dir / file_path
    if asset_file.exists() and asset_file.is_file():
        return FileResponse(asset_file)
    return JSONResponse(status_code=404, content={"detail": "Asset not found"})

# Debug endpoint to list all routes
@app.get("/api/debug/routes")
async def list_routes():
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name
            })
    return {"routes": routes}

# Serve static files - mount after API routes to avoid conflicts
if spa_dir.exists():
    # Mount static files at root, but StaticFiles won't interfere with existing routes
    # This is safe because API routes are already registered and have higher priority
    from fastapi.staticfiles import StaticFiles

    # Use a custom StaticFiles that doesn't claim all routes
    @app.exception_handler(404)
    async def custom_404_handler(request: Request, exc):
        # If it's an API request, return JSON 404
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        # Otherwise, try to serve static file or asset
        path = request.url.path.lstrip("/")
        if path:
            # Try static directory first
            file_path = spa_dir / path
            if file_path.exists() and file_path.is_file():
                # Add no-cache headers for JS, CSS, and HTML files during development
                headers = NO_CACHE_HEADERS if path.endswith(('.js', '.css', '.html')) else {}
                return FileResponse(file_path, headers=headers)

            # Try assets directory
            if path.startswith("assets/"):
                asset_path = assets_dir / path.replace("assets/", "", 1)
                if asset_path.exists() and asset_path.is_file():
                    return FileResponse(asset_path)

        # Fallback to index.html for client-side routing
        index_path = spa_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path, headers=NO_CACHE_HEADERS)

        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    @app.exception_handler(405)
    async def custom_405_handler(request: Request, exc):
        # For debugging: log the 405 error with details
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"405 Method Not Allowed: {request.method} {request.url.path}")

        # If it's an API request, return JSON with allowed methods
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=405, content={"detail": "Method Not Allowed", "method": request.method, "path": request.url.path})

        # For non-API requests, serve index.html
        index_path = spa_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path, headers=NO_CACHE_HEADERS)

        return JSONResponse(status_code=405, content={"detail": "Method Not Allowed"})


def find_available_port(start_port: int = 8000, max_port: int = 8100) -> int:
    """Find an available port starting from start_port."""
    import socket
    
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    
    raise RuntimeError(f"No available ports found between {start_port} and {max_port}")


def start_web_server(port: Optional[int] = None, host: str = "127.0.0.1", no_browser: bool = False):
    """Start the FastAPI web server."""
    if port is None:
        port = find_available_port()
    
    url = f"http://{host}:{port}"
    
    if not no_browser:
        # Schedule browser opening after server starts
        def open_browser():
            import time
            time.sleep(1)  # Wait a moment for server to start
            webbrowser.open_new_tab(url)
        
        # Run the browser opening in a separate thread
        import threading
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
    
    # Configure and start server
    server_config = uvicorn.Config(
        "promptheus.web.server:app",  # Use the app from this module
        host=host,
        port=port,
        log_level="info",
        reload=False,  # Don't enable reload in production
    )
    server = uvicorn.Server(server_config)
    
    print(f"Starting Promptheus Web Server on {url}")
    print(f"Press Ctrl+C to stop the server")
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        return


if __name__ == "__main__":
    start_web_server()
