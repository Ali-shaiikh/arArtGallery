from flask import Blueprint, request, Response, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

from .extensions import db
from .models import User

auth_bp = Blueprint("auth", __name__)

# ---- Auth helpers ----
def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not get_current_user():
            return redirect(url_for("spa.start"))
        return func(*args, **kwargs)
    return wrapper

# ---- Start/Login/Signup (FORM) ----
@auth_bp.route("/signup", methods=["POST"])
def signup():
    try:
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not name or not email or not password:
            return Response("Name, email and password are required", status=400)

        if User.query.filter_by(email=email).first():
            return Response("Account already exists. Please login.", status=400)

        user = User(name=name, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        return redirect(url_for("spa.select_role"))

    except Exception as e:
        db.session.rollback()
        return Response(f"Signup error: {str(e)}", status=500)

@auth_bp.route("/login", methods=["POST"])
def login():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return Response("Invalid email or password", status=401)

    session["user_id"] = user.id
    return redirect(url_for("spa.select_role"))

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("spa.start"))

# ---- Auth API for React SPA ----
@auth_bp.route("/api/me", methods=["GET"])
def api_me():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401

    return jsonify({
        "user": {"id": user.id, "name": user.name, "email": user.email}
    })

@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = user.id
    return jsonify({
        "user": {"id": user.id, "name": user.name, "email": user.email}
    })

@auth_bp.route("/api/signup", methods=["POST"])
def api_signup():
    try:
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not name or not email or not password:
            return jsonify({"error": "Name, email and password are required"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Account already exists. Please login."}), 400

        user = User(name=name, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        return jsonify({
            "user": {"id": user.id, "name": user.name, "email": user.email}
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Signup error: {str(e)}"}), 500
