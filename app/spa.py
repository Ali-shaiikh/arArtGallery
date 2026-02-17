import os
from flask import Blueprint, send_file, send_from_directory, abort, Response, redirect, url_for
from .auth import get_current_user, login_required
from .config import basedir

spa_bp = Blueprint("spa", __name__)

def _spa_index_path():
    return os.path.join(basedir, "frontend", "dist", "index.html")

def _serve_spa_if_built():
    path = _spa_index_path()
    if os.path.isfile(path):
        return send_file(path)
    return None

def _frontend_build_required():
    return Response(
        """<!DOCTYPE html><html><head><meta charset="utf-8"><title>Build required</title></head>
        <body style="font-family:sans-serif;max-width:480px;margin:60px auto;padding:20px;">
        <h1>Frontend not built</h1>
        <p>Build the React frontend first:</p>
        <pre style="background:#f0f0f0;padding:12px;border-radius:8px;">cd frontend && npm install && npm run build</pre>
        <p>Then restart the server and reload this page.</p>
        </body></html>""",
        status=503,
        mimetype="text/html",
    )

@spa_bp.route("/")
def home():
    return _serve_spa_if_built() or redirect(url_for("spa.start"))

@spa_bp.route("/start", methods=["GET"])
def start():
    user = get_current_user()
    if user:
        return redirect(url_for("spa.select_role"))
    return _serve_spa_if_built() or _frontend_build_required()

@spa_bp.route("/assets/<path:path>")
def serve_spa_assets(path):
    dist_assets = os.path.join(basedir, "frontend", "dist", "assets")
    if not os.path.isdir(dist_assets):
        abort(404)
    return send_from_directory(dist_assets, path)

@spa_bp.route("/select-role")
@login_required
def select_role():
    return _serve_spa_if_built() or _frontend_build_required()

@spa_bp.route("/buyer")
@login_required
def buyer_home():
    return _serve_spa_if_built() or _frontend_build_required()

@spa_bp.route("/seller")
@login_required
def seller_home():
    return _serve_spa_if_built() or _frontend_build_required()

@spa_bp.route("/ar-viewer")
def ar_viewer():
    return _serve_spa_if_built() or _frontend_build_required()
