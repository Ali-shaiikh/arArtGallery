import os
import io
import re
import numpy as np
from PIL import Image
import trimesh
from flask import Flask, request, send_file, send_from_directory, abort, Response, redirect, url_for, render_template_string, session, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# ---- Flask App ----
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'artwork.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Database Model
class Artwork(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, default="Untitled Artwork")
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=True)
    artwork_type = db.Column(db.String(50), nullable=True)  # painting, sculpture, digital, etc.
    artist = db.Column(db.String(200), nullable=True)
    year_created = db.Column(db.Integer, nullable=True)
    dimensions = db.Column(db.String(100), nullable=True)  # e.g., "24x36 inches"
    medium = db.Column(db.String(100), nullable=True)  # oil, acrylic, watercolor, etc.
    style = db.Column(db.String(100), nullable=True)  # abstract, realistic, modern, etc.
    image_data = db.Column(db.LargeBinary, nullable=False)
    glb_data = db.Column(db.LargeBinary, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    filename = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<Artwork {self.name}>'

# Simple User model for authentication
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.name} ({self.email})>'

# Create database tables
with app.app_context():
    db.create_all()
# Allow CORS from any origin with any headers - Chrome-friendly configuration
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Credentials", "Cache-Control", "X-Requested-With", "X-Mobile-Request", "X-Connection-Type", "X-Retry-Count"]
    }
})

# Add security headers for AR support
@app.after_request
def add_header(response):
    # Mobile and Chrome-specific CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Authorization, X-Requested-With, Origin, X-Mobile-Request, X-Connection-Type, X-Retry-Count'
    response.headers['Access-Control-Max-Age'] = '86400'  # 24 hours
    response.headers['Access-Control-Allow-Credentials'] = 'false'
    # Remove headers that can cause issues in Chrome and mobile browsers
    response.headers.pop('Cross-Origin-Opener-Policy', None)
    response.headers.pop('Cross-Origin-Embedder-Policy', None)
    response.headers.pop('Cross-Origin-Resource-Policy', None)
    return response

@app.route("/")
def home():
    return _serve_spa_if_built() or redirect(url_for("start"))

# ---- Auth helpers ----
def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)

def login_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not get_current_user():
            return redirect(url_for('start'))
        return func(*args, **kwargs)
    return wrapper

# ---- Start/Login/Signup ----
@app.route("/start", methods=["GET"]) 
def start():
    user = get_current_user()
    if user:
        return redirect(url_for('select_role'))
    return _serve_spa_if_built() or _frontend_build_required()

from werkzeug.security import generate_password_hash, check_password_hash

@app.route("/signup", methods=["POST"]) 
def signup():
    try:
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        if not name or not email or not password:
            return Response("Name, email and password are required", status=400)
        if User.query.filter_by(email=email).first():
            return Response("Account already exists. Please login.", status=400)
        user = User(name=name, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        return redirect(url_for('select_role'))
    except Exception as e:
        db.session.rollback()
        return Response(f"Signup error: {str(e)}", status=500)

@app.route("/login", methods=["POST"]) 
def login():
    email = (request.form.get('email') or '').strip().lower()
    password = request.form.get('password') or ''
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return Response("Invalid email or password", status=401)
    session['user_id'] = user.id
    return redirect(url_for('select_role'))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('start'))

# ---- Auth API for React SPA ----
@app.route("/api/me", methods=["GET"])
def api_me():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    })

@app.route("/api/login", methods=["POST"])
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

@app.route("/api/signup", methods=["POST"])
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

def _spa_index_path():
    return os.path.join(basedir, 'frontend', 'dist', 'index.html')

def _serve_spa_if_built():
    path = _spa_index_path()
    if os.path.isfile(path):
        return send_file(path)
    return None

def _frontend_build_required():
    """Return a simple HTML response when the React frontend has not been built."""
    return Response(
        """<!DOCTYPE html><html><head><meta charset="utf-8"><title>Build required</title></head><body style="font-family:sans-serif;max-width:480px;margin:60px auto;padding:20px;">
        <h1>Frontend not built</h1>
        <p>Build the React frontend first:</p>
        <pre style="background:#f0f0f0;padding:12px;border-radius:8px;">cd frontend && npm install && npm run build</pre>
        <p>Then restart the server and reload this page.</p>
        </body></html>""",
        status=503,
        mimetype="text/html",
    )

@app.route("/assets/<path:path>")
def serve_spa_assets(path):
    dist_assets = os.path.join(basedir, 'frontend', 'dist', 'assets')
    if not os.path.isdir(dist_assets):
        abort(404)
    return send_from_directory(dist_assets, path)

# ---- Role selection ----
@app.route("/select-role")
@login_required
def select_role():
    return _serve_spa_if_built() or _frontend_build_required()

# ---- Buyer marketplace ----
@app.route("/buyer")
@login_required
def buyer_home():
    return _serve_spa_if_built() or _frontend_build_required()

# ---- Seller redirect to upload page ----
@app.route("/seller")
@login_required
def seller_home():
    return _serve_spa_if_built() or _frontend_build_required()

# ---- AR Viewer ----
@app.route("/ar-viewer")
def ar_viewer():
    return _serve_spa_if_built() or _frontend_build_required()

@app.route("/health", methods=["GET", "OPTIONS"])
def health_check():
    # Simple health check endpoint for testing connectivity
    if request.method == "OPTIONS":
        response = Response(status=200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, X-Mobile-Request'
        return response
    
    # Detect if this is a mobile request
    is_mobile = request.headers.get('X-Mobile-Request', 'false') == 'true'
    user_agent = request.headers.get('User-Agent', 'unknown')
    
    health_info = {
        "status": "OK",
        "timestamp": datetime.now().isoformat(),
        "mobile_detected": is_mobile,
        "user_agent": user_agent[:100]  # Truncate for security
    }
    
    if request.headers.get('Accept', '').startswith('application/json'):
        return jsonify(health_info)
    else:
        return Response(f"OK - Mobile: {is_mobile}", status=200, mimetype='text/plain')

def create_glb_from_image(file_like, width_m=0.6, thickness_m=0.01):
    try:
        # Convert to RGB to ensure full opacity (no transparency)
        img = Image.open(file_like).convert("RGB")
        
        # Enhance contrast and saturation for better visibility in AR
        from PIL import ImageEnhance
        
        # Increase contrast slightly
        contrast_enhancer = ImageEnhance.Contrast(img)
        img = contrast_enhancer.enhance(1.2)
        
        # Increase saturation for more vibrant colors
        color_enhancer = ImageEnhance.Color(img)
        img = color_enhancer.enhance(1.1)
        
        w_px, h_px = img.size
        
        # Validate image dimensions
        if w_px == 0 or h_px == 0:
            raise ValueError("Invalid image dimensions")
        
        aspect = h_px / float(w_px)

        # Fixed dimensions - 60cm width for realistic artwork size
        W = float(width_m)
        H = W * aspect
        T = float(thickness_m)

        box = trimesh.creation.box(extents=(W, H, T))
        box.apply_translation((0, 0, T/2.0))

        # Create UV mapping for better texture application
        uv = np.zeros((len(box.vertices), 2), dtype=np.float32)
        verts = box.vertices
        min_xy = verts[:, :2].min(axis=0)
        max_xy = verts[:, :2].max(axis=0)
        span_xy = np.maximum(max_xy - min_xy, 1e-8)
        uv[:] = (verts[:, :2] - min_xy) / span_xy

        # Apply texture with full opacity
        texture = trimesh.visual.texture.TextureVisuals(uv=uv, image=img)
        box.visual = texture

        # Export with optimized settings for AR visibility
        glb_bytes = box.export(file_type="glb")
        return glb_bytes if isinstance(glb_bytes, bytes) else glb_bytes.read()
        
    except Exception as e:
        print(f"Error in create_glb_from_image: {str(e)}")
        return None

@app.route("/make-glb", methods=["POST", "OPTIONS"])
def make_glb():
    # Handle CORS preflight requests - Mobile and Chrome-friendly
    if request.method == "OPTIONS":
        response = Response(status=200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Authorization, X-Requested-With, Origin, X-Mobile-Request, X-Connection-Type, X-Retry-Count'
        response.headers['Access-Control-Max-Age'] = '86400'
        response.headers['Access-Control-Allow-Credentials'] = 'false'
        response.headers['Content-Length'] = '0'
        return response
    
    try:
        # Validate request
        if 'image' not in request.files:
            print("Debug: No 'image' in request.files")
            print("Debug: Available keys:", list(request.files.keys()))
            return Response('{"success": false, "error": "No file uploaded. Please select an image file."}', 
                          mimetype="application/json", status=400)
        
        f = request.files['image']
        
        # Check if file is selected
        if f.filename == '':
            return Response('{"success": false, "error": "No file selected. Please choose an image."}', 
                          mimetype="application/json", status=400)
        
        # Basic file type validation
        if not f.content_type or not f.content_type.startswith('image/'):
            return Response('{"success": false, "error": "Invalid file type. Please upload an image file (JPG, PNG, etc.)."}', 
                          mimetype="application/json", status=400)
        
        # Get form data
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price_str = request.form.get('price', '').strip()
        artwork_type = request.form.get('artwork_type', '').strip()
        artist = request.form.get('artist', '').strip()
        year_created_str = request.form.get('year_created', '').strip()
        dimensions = request.form.get('dimensions', '').strip()
        medium = request.form.get('medium', '').strip()
        style = request.form.get('style', '').strip()
        
        # Debug logging with mobile detection
        is_mobile_request = request.headers.get('X-Mobile-Request', 'false') == 'true'
        connection_type = request.headers.get('X-Connection-Type', 'unknown')
        retry_count = request.headers.get('X-Retry-Count', '0')
        user_agent = request.headers.get('User-Agent', 'unknown')
        
        print(f"Make-GLB Request - Mobile: {is_mobile_request}, Connection: {connection_type}, Retry: {retry_count}")
        print(f"Form data: name={name}, artist={artist}, price={price_str}, type={artwork_type}")
        print(f"User-Agent: {user_agent}")
        
        if is_mobile_request:
            print("Mobile device detected - using mobile-optimized processing")
        
        # Validate required fields
        if not name:
            return Response('{"success": false, "error": "Artwork name is required."}', 
                          mimetype="application/json", status=400)
        
        # Convert price and year to appropriate types
        price = float(price_str) if price_str else None
        year_created = int(year_created_str) if year_created_str else None
        
        # Read image data
        image_data = f.read()
        
        # Process the image to create GLB
        glb_bytes = create_glb_from_image(io.BytesIO(image_data))
        
        if not glb_bytes:
            return Response('{"success": false, "error": "Failed to process image. Please try a different image."}', 
                          mimetype="application/json", status=500)
        
        # Store in database
        artwork = Artwork(
            name=name,
            description=description,
            price=price,
            artwork_type=artwork_type,
            artist=artist,
            year_created=year_created,
            dimensions=dimensions,
            medium=medium,
            style=style,
            image_data=image_data,
            glb_data=glb_bytes,
            filename=f.filename
        )
        
        db.session.add(artwork)
        db.session.commit()
        
        print(f"Artwork saved with ID: {artwork.id}")
        
        # Return the artwork ID as JSON
        return Response(
            f'{{"success": true, "artwork_id": {artwork.id}}}',
            mimetype="application/json",
            status=200
        )
        
    except Exception as e:
        print(f"Error in make_glb: {str(e)}")  # Server-side logging
        db.session.rollback()
        
        # Return JSON error response instead of plain text
        return Response(
            f'{{"success": false, "error": "Server error while processing image: {str(e)}"}}',
            mimetype="application/json",
            status=500
        )

@app.route("/artwork/<int:artwork_id>/image")
def artwork_image(artwork_id):
    """Return the artwork image binary (PNG/JPEG)."""
    art = Artwork.query.get_or_404(artwork_id)
    img_bytes = getattr(art, "image_data", None) or getattr(art, "image", None)
    if not img_bytes:
        abort(404, "Image not found")
    return send_file(io.BytesIO(img_bytes), mimetype="image/png", download_name=f"artwork-{artwork_id}.png")

@app.route("/artwork/<int:artwork_id>/glb")
def artwork_glb(artwork_id):
    """Return the artwork GLB binary (gltf-binary)."""
    art = Artwork.query.get_or_404(artwork_id)
    glb_bytes = getattr(art, "glb_data", None) or getattr(art, "glb", None)
    if not glb_bytes:
        abort(404, "GLB not found")
    return send_file(io.BytesIO(glb_bytes), mimetype="model/gltf-binary", download_name=f"artwork-{artwork_id}.glb")

@app.route("/artwork/<int:artwork_id>")
def artwork_page(artwork_id):
    spa = _serve_spa_if_built()
    if spa is not None:
        return spa
    art = Artwork.query.get_or_404(artwork_id)
    recs = recommend_similar_artworks(art, top_n=6)
    # Simple inline HTML; integrate into your frontend templates as needed.
    template = """
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>{{ art.name }} — Viewer</title>
        <style>
          body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; padding: 20px; }
          .main { display:flex; gap:20px; align-items:flex-start; }
          .thumb { max-width:420px; border:1px solid #ddd; padding:8px; background:#fff; }
          .meta { max-width:480px; }
          .recs { margin-top:30px; }
          .rec-list { display:flex; gap:12px; flex-wrap:wrap; }
          .rec-item { width:160px; border:1px solid #eee; padding:8px; text-align:center; background:#fafafa; }
          .rec-item img { width:100%; height:100px; object-fit:cover; display:block; }
          a { color: #0366d6; text-decoration:none; }
        </style>
      </head>
      <body>
        <div class="main">
          <div>
            <img class="thumb" src="{{ url_for('artwork_image', artwork_id=art.id) }}" alt="{{ art.name }}">
            <p><a href="{{ url_for('artwork_glb', artwork_id=art.id) }}">Download GLB</a></p>
          </div>
          <div class="meta">
            <h1>{{ art.name }}</h1>
            <p><strong>Artist:</strong> {{ art.artist or 'Unknown' }}</p>
            <p><strong>Type:</strong> {{ art.artwork_type or '—' }} · <strong>Style:</strong> {{ art.style or '—' }} · <strong>Medium:</strong> {{ art.medium or '—' }}</p>
            <p>{{ art.description or '' }}</p>
            <p><em>Created at: {{ art.created_at }}</em></p>
          </div>
        </div>

        <div class="recs">
          <h2>Similar artworks</h2>
          {% if recs %}
          <div class="rec-list">
            {% for r in recs %}
            <div class="rec-item">
              <a href="{{ url_for('artwork_page', artwork_id=r.id) }}">
                <img src="{{ url_for('artwork_image', artwork_id=r.id) }}" alt="{{ r.name }}">
                <div style="margin-top:6px;font-weight:600;">{{ r.name[:30] }}</div>
                <div style="font-size:13px;color:#555;">{{ r.artist or '' }}</div>
                <div style="font-size:12px;color:#888;margin-top:4px;">score: {{ r.score }}</div>
              </a>
            </div>
            {% endfor %}
          </div>
          {% else %}
            <p>No similar artworks found.</p>
          {% endif %}
        </div>
      </body>
    </html>
    """
    return render_template_string(template, art=art, recs=recs)

@app.route("/api/artwork/<int:artwork_id>", methods=["GET"])
def get_artwork_api(artwork_id):
    artwork = Artwork.query.get_or_404(artwork_id)
    return jsonify({
        'id': artwork.id,
        'name': artwork.name,
        'description': artwork.description,
        'price': artwork.price,
        'artwork_type': artwork.artwork_type,
        'artist': artwork.artist,
        'year_created': artwork.year_created,
        'dimensions': artwork.dimensions,
        'medium': artwork.medium,
        'style': artwork.style,
        'created_at': artwork.created_at.isoformat() if artwork.created_at else None,
        'filename': artwork.filename
    })

# List artworks (JSON) - must be registered so /artworks is not shadowed by SPA
@app.route("/artworks", methods=["GET"])
def list_artworks():
    try:
        artworks = Artwork.query.order_by(Artwork.created_at.desc()).all()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    data = []
    for a in artworks:
        data.append({
            'id': a.id,
            'name': a.name,
            'artist': a.artist,
            'artwork_type': a.artwork_type,
            'price': a.price,
            'description': a.description,
            'year_created': a.year_created,
            'dimensions': a.dimensions,
            'medium': a.medium,
            'style': a.style,
            'created_at': a.created_at.isoformat() if a.created_at else None
        })
    return jsonify(data)

# Update artwork (PUT)
@app.route("/api/artwork/<int:artwork_id>", methods=["PUT"])
def update_artwork(artwork_id):
    try:
        artwork = Artwork.query.get_or_404(artwork_id)
        
        # Get JSON data from request
        data = request.get_json()
        
        # Update fields if provided
        if 'name' in data:
            artwork.name = data['name'].strip()
        if 'description' in data:
            artwork.description = data['description'].strip()
        if 'price' in data:
            artwork.price = float(data['price']) if data['price'] else None
        if 'artwork_type' in data:
            artwork.artwork_type = data['artwork_type'].strip()
        if 'artist' in data:
            artwork.artist = data['artist'].strip()
        if 'year_created' in data:
            artwork.year_created = int(data['year_created']) if data['year_created'] else None
        if 'dimensions' in data:
            artwork.dimensions = data['dimensions'].strip()
        if 'medium' in data:
            artwork.medium = data['medium'].strip()
        if 'style' in data:
            artwork.style = data['style'].strip()
        
        db.session.commit();
        
        return jsonify({
            'success': True,
            'message': 'Artwork updated successfully',
            'artwork': {
                'id': artwork.id,
                'name': artwork.name,
                'description': artwork.description,
                'price': artwork.price,
                'artwork_type': artwork.artwork_type,
                'artist': artwork.artist,
                'year_created': artwork.year_created,
                'dimensions': artwork.dimensions,
                'medium': artwork.medium,
                'style': artwork.style,
                'created_at': artwork.created_at.isoformat(),
                'filename': artwork.filename
            }
        })
        
    except Exception as e:
        db.session.rollback();
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Delete artwork (DELETE)
@app.route("/api/artwork/<int:artwork_id>", methods=["DELETE"])
def delete_artwork(artwork_id):
    try:
        artwork = Artwork.query.get_or_404(artwork_id)
        artwork_name = artwork.name;
        
        db.session.delete(artwork);
        db.session.commit();
        
        return jsonify({
            'success': True,
            'message': f'Artwork "{artwork_name}" deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback();
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Gallery Management - Auto-populate artworks
@app.route("/admin/populate", methods=["GET", "POST"])
def populate_gallery():
    if request.method == "GET":
        # Count existing artworks and images in data folder
        artwork_count = Artwork.query.count()
        
        data_folder = os.path.join(basedir, 'data')
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
        image_count = 0
        
        if os.path.exists(data_folder):
            for filename in os.listdir(data_folder):
                if os.path.isfile(os.path.join(data_folder, filename)):
                    _, ext = os.path.splitext(filename.lower())
                    if ext in image_extensions:
                        image_count += 1
        
        return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Gallery Population - AR Art Gallery</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; margin-bottom: 30px; }
        .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #e3f2fd; padding: 20px; border-radius: 8px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #1976d2; }
        .stat-label { color: #666; margin-top: 5px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
        input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { background: #4CAF50; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #45a049; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        .info { background: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        .instructions { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .instructions h3 { margin-top: 0; color: #333; }
        .instructions ul { margin: 0; padding-left: 20px; }
        .instructions li { margin-bottom: 8px; }
        #status { margin-top: 20px; padding: 15px; border-radius: 4px; display: none; }
        .success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨 AR Gallery Auto-Population</h1>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ artwork_count }}</div>
                <div class="stat-label">Artworks in Gallery</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ image_count }}</div>
                <div class="stat-label">Images in Data Folder</div>
            </div>
        </div>
        
        {% if image_count == 0 %}
        <div class="warning">
            <strong>⚠️ No images found!</strong><br>
            Please add artwork images to the <code>data</code> folder before proceeding.
        </div>
        {% endif %}
        
        <div class="instructions">
            <h3>📋 How to Add Artworks:</h3>
            <ul>
                <li>Add artwork images (JPG, PNG, etc.) to the <code>data</code> folder</li>
                <li>Enter your Gemini API key below for AI-generated descriptions (optional)</li>
                <li>Click "Process Images" to automatically add them to the gallery</li>
                <li>The system will generate realistic artist names, prices, and metadata</li>
                <li>All artworks will appear on the buyer page immediately</li>
            </ul>
        </div>
        
        <form id="populateForm" method="POST">
            <div class="form-group">
                <label for="gemini_api_key">Gemini API Key (Optional but Recommended):</label>
                <input type="password" id="gemini_api_key" name="gemini_api_key" 
                       placeholder="Enter your Gemini API key for AI-generated descriptions">
                <small style="color: #666; display: block; margin-top: 5px;">
                    Get your free API key from <a href="https://makersuite.google.com/app/apikey" target="_blank">Google AI Studio</a>
                </small>
            </div>
            
            <button type="submit" id="submitBtn" {% if image_count == 0 %}disabled{% endif %}>
                🚀 Process {{ image_count }} Image(s) and Add to Gallery
            </button>
        </form>
        
        <div id="status"></div>
        
        {% if artwork_count > 0 %}
        <div class="info" style="margin-top: 30px;">
            <strong>🎉 Gallery Status:</strong> You have {{ artwork_count }} artwork(s) in your gallery!<br>
            <a href="/buyer" target="_blank" style="color: #1976d2; text-decoration: none; font-weight: bold;">
                → View Gallery (Buyer Page)
            </a>
        </div>
        {% endif %}
    </div>
    
    <script>
        document.getElementById('populateForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submitBtn = document.getElementById('submitBtn');
            const status = document.getElementById('status');
            const formData = new FormData(this);
            
            // Show loading state
            submitBtn.disabled = true;
            submitBtn.textContent = '🔄 Processing images...';
            status.style.display = 'block';
            status.className = 'info';
            status.innerHTML = 'Processing images and generating descriptions. This may take a few minutes...';
            
            try {
                const response = await fetch('/admin/populate', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    status.className = 'success';
                    status.innerHTML = `
                        <strong>🎉 Success!</strong><br>
                        Added ${result.processed} artwork(s) to the gallery.<br>
                        <a href="/buyer" target="_blank" style="color: #155724; font-weight: bold;">→ View Gallery</a>
                    `;
                    
                    // Refresh page after 3 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 3000);
                } else {
                    status.className = 'error';
                    status.innerHTML = `<strong>❌ Error:</strong> ${result.error}`;
                }
            } catch (error) {
                status.className = 'error';
                status.innerHTML = `<strong>❌ Error:</strong> ${error.message}`;
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = '🚀 Process Images and Add to Gallery';
            }
        });
    </script>
</body>
</html>
        """, artwork_count=artwork_count, image_count=image_count)
    
    elif request.method == "POST":
        try:
            gemini_api_key = request.form.get('gemini_api_key', '').strip()
            
            # Import the populator (we'll create a simplified version)
            from populate_artworks import ArtworkPopulator
            
            populator = ArtworkPopulator(gemini_api_key if gemini_api_key else None)
            data_folder = os.path.join(basedir, 'data')
            
            # Count images before processing
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
            initial_count = Artwork.query.count()
            
            # Process images
            populator.populate_from_folder(data_folder)
            
            # Count images after processing
            final_count = Artwork.query.count()
            processed = final_count - initial_count
            
            return jsonify({
                'success': True,
                'processed': processed,
                'total_artworks': final_count
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


@app.route("/database")
def view_database():
    artworks = Artwork.query.all()
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Artwork Database</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .artwork { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 8px; }
            .artwork h3 { margin-top: 0; color: #333; }
            .field { margin: 5px 0; }
            .field strong { display: inline-block; width: 120px; }
            .stats { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <h1>🎨 Artwork Database</h1>
        <div class="stats">
            <h3>Database Statistics</h3>
            <p><strong>Total Artworks:</strong> {{ artworks|length }}</p>
        </div>
        
        {% for artwork in artworks %}
        <div class="artwork">
            <h3>{{ artwork.name }}</h3>
            <div class="field"><strong>ID:</strong> {{ artwork.id }}</div>
            <div class="field"><strong>Artist:</strong> {{ artwork.artist or 'Not specified' }}</div>
            <div class="field"><strong>Type:</strong> {{ artwork.artwork_type or 'Not specified' }}</div>
            <div class="field"><strong>Price:</strong> ${{ "%.2f"|format(artwork.price) if artwork.price else 'Not specified' }}</div>
            <div class="field"><strong>Year:</strong> {{ artwork.year_created or 'Not specified' }}</div>
            <div class="field"><strong>Medium:</strong> {{ artwork.medium or 'Not specified' }}</div>
            <div class="field"><strong>Dimensions:</strong> {{ artwork.dimensions or 'Not specified' }}</div>
            <div class="field"><strong>Style:</strong> {{ artwork.style or 'Not specified' }}</div>
            <div class="field"><strong>Description:</strong> {{ artwork.description or 'No description' }}</div>
            <div class="field"><strong>Created:</strong> {{ artwork.created_at.strftime('%Y-%m-%d %H:%M:%S') if artwork.created_at else 'Unknown' }}</div>
            <div class="field"><strong>Filename:</strong> {{ artwork.filename }}</div>
        </div>
        {% endfor %}
    </body>
    </html>
    """, artworks=artworks)

@app.route("/viewer")
def viewer():
    html = """
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AR Image Viewer</title>
        <script type="module" src="https://unpkg.com/@google/model-viewer@v1.12.0/dist/model-viewer.min.js"></script>
        <style>
          body {
            font-family: 'Arial', sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            text-align: center;
          }
          h2 {
            color: #333;
            font-size: 1.5rem;
          }
          .input-area {
            margin: 20px 0;
          }
          input[type="file"] {
            margin-right: 10px;
            max-width: 100%;
          }
          button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin: 5px;
          }
          button:hover {
            background-color: #45a049;
          }
          #ar-button {
            background-color: #2196F3;
            margin-top: 10px;
            display: none;
            font-weight: bold;
            padding: 12px 20px;
            font-size: 1.1rem;
          }
          #ar-button:hover {
            background-color: #0b7dda;
          }
          model-viewer {
            width: 100%;
            height: 60vh;
            margin-top: 20px;
            background-color: #f5f5f5;
            border-radius: 8px;
          }
          #status {
            margin: 10px 0;
            padding: 10px;
            border-radius: 4px;
            display: none;
          }
          .success {
            background-color: #d4edda;
            color: #155724;
          }
          .error {
            background-color: #f8d7da;
            color: #721c24;
          }
          .info {
            background-color: #e2f3f8;
            color: #0c5460;
          }
          .ar-instructions {
            display: none;
            margin-top: 15px;
            padding: 10px;
            background-color: #fff3cd;
            color: #856404;
            border-radius: 4px;
            text-align: left;
          }
          @media (max-width: 600px) {
            .input-area {
              display: flex;
              flex-direction: column;
              align-items: center;
            }
            input[type="file"] {
              margin-right: 0;
              margin-bottom: 10px;
              width: 100%;
            }
          }
        </style>
      </head>
      <body>
        <h2>Upload your artwork and view it in AR</h2>
        <div class="input-area">
          <input id="file" type="file" accept="image/*" />
          
          <div class="artwork-form" style="margin: 20px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
            <h3 style="margin-top: 0; color: #333;">Artwork Details</h3>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
              <div>
                <label for="name" style="display: block; margin-bottom: 5px; font-weight: bold;">Artwork Name *</label>
                <input type="text" id="name" placeholder="Enter artwork name" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;" required>
              </div>
              
              <div>
                <label for="artist" style="display: block; margin-bottom: 5px; font-weight: bold;">Artist</label>
                <input type="text" id="artist" placeholder="Artist name" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
              </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-bottom: 15px;">
              <div>
                <label for="price" style="display: block; margin-bottom: 5px; font-weight: bold;">Price ($)</label>
                <select id="price" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
                  <option value="">Select price range</option>
                  <option value="50">$50</option>
                  <option value="100">$100</option>
                  <option value="250">$250</option>
                  <option value="500">$500</option>
                  <option value="1000">$1,000</option>
                  <option value="2500">$2,500</option>
                  <option value="5000">$5,000</option>
                  <option value="10000">$10,000</option>
                  <option value="25000">$25,000</option>
                  <option value="50000">$50,000+</option>
                </select>
              </div>
              
              <div>
                <label for="artwork_type" style="display: block; margin-bottom: 5px; font-weight: bold;">Type</label>
                <select id="artwork_type" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
                  <option value="">Select type</option>
                  <option value="painting">Painting</option>
                  <option value="sculpture">Sculpture</option>
                  <option value="photography">Photography</option>
                  <option value="digital">Digital Art</option>
                  <option value="print">Print</option>
                  <option value="mixed_media">Mixed Media</option>
                  <option value="other">Other</option>
                </select>
              </div>
              
              <div>
                <label for="year_created" style="display: block; margin-bottom: 5px; font-weight: bold;">Year Created</label>
                <select id="year_created" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
                  <option value="">Select year</option>
                  <option value="2025">2025</option>
                  <option value="2024">2024</option>
                  <option value="2023">2023</option>
                  <option value="2022">2022</option>
                  <option value="2021">2021</option>
                  <option value="2020">2020</option>
                  <option value="2019">2019</option>
                  <option value="2018">2018</option>
                  <option value="2017">2017</option>
                  <option value="2016">2016</option>
                  <option value="2015">2015</option>
                  <option value="2014">2014</option>
                  <option value="2013">2013</option>
                  <option value="2012">2012</option>
                  <option value="2011">2011</option>
                  <option value="2010">2010</option>
                  <option value="2009">2009</option>
                  <option value="2008">2008</option>
                  <option value="2007">2007</option>
                  <option value="2006">2006</option>
                  <option value="2005">2005</option>
                  <option value="2004">2004</option>
                  <option value="2003">2003</option>
                  <option value="2002">2002</option>
                  <option value="2001">2001</option>
                  <option value="2000">2000</option>
                  <option value="1999">1999</option>
                  <option value="1998">1998</option>
                  <option value="1997">1997</option>
                  <option value="1996">1996</option>
                  <option value="1995">1995</option>
                  <option value="1994">1994</option>
                  <option value="1993">1993</option>
                  <option value="1992">1992</option>
                  <option value="1991">1991</option>
                  <option value="1990">1990</option>
                  <option value="1989">1989</option>
                  <option value="1988">1988</option>
                  <option value="1987">1987</option>
                  <option value="1986">1986</option>
                  <option value="1985">1985</option>
                  <option value="1984">1984</option>
                  <option value="1983">1983</option>
                  <option value="1982">1982</option>
                  <option value="1981">1981</option>
                  <option value="1980">1980</option>
                  <option value="1979">1979</option>
                  <option value="1978">1978</option>
                  <option value="1977">1977</option>
                  <option value="1976">1976</option>
                  <option value="1975">1975</option>
                  <option value="1974">1974</option>
                  <option value="1973">1973</option>
                  <option value="1972">1972</option>
                  <option value="1971">1971</option>
                  <option value="1970">1970</option>
                  <option value="1969">1969</option>
                  <option value="1968">1968</option>
                  <option value="1967">1967</option>
                  <option value="1966">1966</option>
                  <option value="1965">1965</option>
                  <option value="1964">1964</option>
                  <option value="1963">1963</option>
                  <option value="1962">1962</option>
                  <option value="1961">1961</option>
                  <option value="1960">1960</option>
                  <option value="1959">1959</option>
                  <option value="1958">1958</option>
                  <option value="1957">1957</option>
                  <option value="1956">1956</option>
                  <option value="1955">1955</option>
                  <option value="1954">1954</option>
                  <option value="1953">1953</option>
                  <option value="1952">1952</option>
                  <option value="1951">1951</option>
                  <option value="1950">1950</option>
                  <option value="1949">1949</option>
                  <option value="1948">1948</option>
                  <option value="1947">1947</option>
                  <option value="1946">1946</option>
                  <option value="1945">1945</option>
                  <option value="1944">1944</option>
                  <option value="1943">1943</option>
                  <option value="1942">1942</option>
                  <option value="1941">1941</option>
                  <option value="1940">1940</option>
                  <option value="1939">1939</option>
                  <option value="1938">1938</option>
                  <option value="1937">1937</option>
                  <option value="1936">1936</option>
                  <option value="1935">1935</option>
                  <option value="1934">1934</option>
                  <option value="1933">1933</option>
                  <option value="1932">1932</option>
                  <option value="1931">1931</option>
                  <option value="1930">1930</option>
                  <option value="1929">1929</option>
                  <option value="1928">1928</option>
                  <option value="1927">1927</option>
                  <option value="1926">1926</option>
                  <option value="1925">1925</option>
                </select>
              </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
              <div>
                <label for="medium" style="display: block; margin-bottom: 5px; font-weight: bold;">Medium</label>
                <select id="medium" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
                  <option value="">Select medium</option>
                  <option value="oil">Oil</option>
                  <option value="acrylic">Acrylic</option>
                  <option value="watercolor">Watercolor</option>
                  <option value="gouache">Gouache</option>
                  <option value="pastel">Pastel</option>
                  <option value="charcoal">Charcoal</option>
                  <option value="pencil">Pencil</option>
                  <option value="ink">Ink</option>
                  <option value="mixed_media">Mixed Media</option>
                  <option value="photography">Photography</option>
                  <option value="digital">Digital</option>
                  <option value="printmaking">Printmaking</option>
                  <option value="sculpture">Sculpture</option>
                  <option value="ceramics">Ceramics</option>
                  <option value="metal">Metal</option>
                  <option value="wood">Wood</option>
                  <option value="stone">Stone</option>
                  <option value="glass">Glass</option>
                  <option value="textile">Textile</option>
                  <option value="other">Other</option>
                </select>
              </div>
              
              <div>
                <label for="dimensions" style="display: block; margin-bottom: 5px; font-weight: bold;">Dimensions</label>
                <select id="dimensions" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
                  <option value="">Select dimensions</option>
                  <option value="8x10 inches">8x10 inches</option>
                  <option value="11x14 inches">11x14 inches</option>
                  <option value="16x20 inches">16x20 inches</option>
                  <option value="18x24 inches">18x24 inches</option>
                  <option value="20x24 inches">20x24 inches</option>
                  <option value="24x30 inches">24x30 inches</option>
                  <option value="24x36 inches">24x36 inches</option>
                  <option value="30x40 inches">30x40 inches</option>
                  <option value="36x48 inches">36x48 inches</option>
                  <option value="40x60 inches">40x60 inches</option>
                  <option value="48x72 inches">48x72 inches</option>
                  <option value="60x80 inches">60x80 inches</option>
                  <option value="72x96 inches">72x96 inches</option>
                  <option value="A4">A4 (8.3x11.7 inches)</option>
                  <option value="A3">A3 (11.7x16.5 inches)</option>
                  <option value="A2">A2 (16.5x23.4 inches)</option>
                  <option value="A1">A1 (23.4x33.1 inches)</option>
                  <option value="A0">A0 (33.1x46.8 inches)</option>
                  <option value="30x30 cm">30x30 cm</option>
                  <option value="40x40 cm">40x40 cm</option>
                  <option value="50x50 cm">50x50 cm</option>
                  <option value="60x60 cm">60x60 cm</option>
                  <option value="70x70 cm">70x70 cm</option>
                  <option value="80x80 cm">80x80 cm</option>
                  <option value="90x90 cm">90x90 cm</option>
                  <option value="100x100 cm">100x100 cm</option>
                  <option value="120x120 cm">120x120 cm</option>
                  <option value="150x150 cm">150x150 cm</option>
                  <option value="200x200 cm">200x200 cm</option>
                  <option value="custom">Custom dimensions</option>
                </select>
              </div>
            </div>
            
            <div style="margin-bottom: 15px;">
              <label for="style" style="display: block; margin-bottom: 5px; font-weight: bold;">Style</label>
              <select id="style" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
                <option value="">Select style</option>
                <option value="abstract">Abstract</option>
                <option value="realistic">Realistic</option>
                <option value="impressionist">Impressionist</option>
                <option value="expressionist">Expressionist</option>
                <option value="surrealist">Surrealist</option>
                <option value="cubist">Cubist</option>
                <option value="minimalist">Minimalist</option>
                <option value="pop_art">Pop Art</option>
                <option value="street_art">Street Art</option>
                <option value="contemporary">Contemporary</option>
                <option value="modern">Modern</option>
                <option value="classical">Classical</option>
                <option value="renaissance">Renaissance</option>
                <option value="baroque">Baroque</option>
                <option value="romantic">Romantic</option>
                <option value="art_nouveau">Art Nouveau</option>
                <option value="art_deco">Art Deco</option>
                <option value="folk_art">Folk Art</option>
                <option value="primitive">Primitive</option>
                <option value="photorealism">Photorealism</option>
                <option value="hyperrealism">Hyperrealism</option>
                <option value="conceptual">Conceptual</option>
                <option value="figurative">Figurative</option>
                <option value="landscape">Landscape</option>
                <option value="portrait">Portrait</option>
                <option value="still_life">Still Life</option>
                <option value="genre">Genre</option>
                <option value="historical">Historical</option>
                <option value="religious">Religious</option>
                <option value="mythological">Mythological</option>
                <option value="other">Other</option>
              </select>
            </div>
            
            <div>
              <label for="description" style="display: block; margin-bottom: 5px; font-weight: bold;">Description</label>
              <textarea id="description" placeholder="Describe your artwork..." rows="4" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; resize: vertical; box-sizing: border-box;"></textarea>
            </div>
          </div>
          
          <button id="btn">Create 3D Model & Save Artwork</button>
        </div>
        <div id="status"></div>
        <div id="artwork-info" style="margin: 20px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6; display: none;">
          <h3 id="artwork-title" style="margin-top: 0; color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px;"></h3>
          <div id="artwork-description" style="line-height: 1.6;"></div>
        </div>
        <button id="ar-button">View in AR</button>
        <div id="ar-instructions" class="ar-instructions">
          <strong>AR Instructions:</strong>
          <ul>
            <li>iOS devices: The model will open in Quick Look AR.</li>
            <li>Android devices: The model will open in Scene Viewer AR.</li>
            <li>You'll need to allow camera permissions for AR to work.</li>
            <li>Position your device toward a wall to place the artwork.</li>
            <li><strong>Fixed Size:</strong> Artwork appears at real-world size (60cm width) - no scaling allowed.</li>
          </ul>
        </div>
        <!-- AR Viewer - Fixed scale version with maximum opacity -->
        <model-viewer id="ar-viewer"
                      ar
                      ar-modes="webxr scene-viewer quick-look"
                      ar-scale="fixed"
                      ar-placement="wall"
                      disable-zoom
                      disable-pan
                      camera-controls
                      shadow-intensity="0.1"
                      exposure="0.5"
                      auto-rotate
                      scale="1 1 1"
                      min-camera-orbit="auto auto auto"
                      max-camera-orbit="auto auto auto"
                      min-field-of-view="auto"
                      max-field-of-view="auto"
                      environment-image="legacy"
                      tone-mapping="commerce"
                      skybox-image=""
                      style="width: 100%; height: 400px; background-color: #f0f0f0; border-radius: 8px;"
                      poster="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect width='100' height='100' fill='%23f0f0f0'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23666'%3EUpload Image%3C/text%3E%3C/svg%3E">
        </model-viewer>        <script>
        document.addEventListener('DOMContentLoaded', function() {
          const viewer = document.getElementById("ar-viewer");
          const arButton = document.getElementById("ar-button");
          const status = document.getElementById("status");
          const arInstructions = document.getElementById("ar-instructions");
          
          // Check if elements exist to prevent null errors
          if (!viewer) {
            console.error("AR viewer element not found");
            return;
          }
          if (!arButton) {
            console.error("AR button element not found");
            return;
          }
          if (!status) {
            console.error("Status element not found");
            return;
          }
          
          // Mobile connectivity and device checks
          const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
          const checkNetworkConnectivity = () => {
            if (!navigator.onLine) {
              showStatus("No internet connection detected. Please check your connection.", "error");
              return false;
            }
            
            if (navigator.connection) {
              const connection = navigator.connection;
              if (connection.effectiveType === 'slow-2g') {
                showStatus("Slow connection detected. Upload may take longer.", "info");
              }
            }
            
            return true;
          };
          
          // Listen for connectivity changes on mobile
          if (isMobile) {
            window.addEventListener('online', () => {
              showStatus("Internet connection restored", "success");
            });
            
            window.addEventListener('offline', () => {
              showStatus("Internet connection lost", "error");
            });
          }
          
          // Check if AR is supported
          const isARSupported = () => {
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
            const isAndroid = /Android/.test(navigator.userAgent);
            const isChrome = /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
            
            // Check for WebXR support (needed for Chrome AR)
            const hasWebXR = 'xr' in navigator && 'isSessionSupported' in navigator.xr;
            
            if (isIOS) {
              // iOS requires version 12+ for AR Quick Look
              const versionMatch = navigator.userAgent.match(/OS ([0-9]+)_([0-9]+)_?([0-9]+)?/);
              if (versionMatch) {
                const version = parseInt(versionMatch[1], 10);
                return version >= 12;
              }
            }
            
            // Chrome on Android needs WebXR or Scene Viewer
            if (isAndroid && isChrome) {
              // Chrome 79+ on Android 8.0+ should support AR
              const match = navigator.userAgent.match(/Chrome\\/([0-9]+)/);
              if (match) {
                const version = parseInt(match[1], 10);
                return version >= 79 || hasWebXR;
              }
            }
            
            // General Android support check
            return isAndroid;
          };
          
          // Show status message
          const showStatus = (message, type) => {
            status.textContent = message;
            status.className = type;
            status.style.display = "block";
            
            // Keep launching messages visible longer
            const duration = (type === "info" && message.includes("Launching")) ? 8000 : 5000;
            
            setTimeout(() => {
              status.style.display = "none";
            }, duration);
          };

          // Check camera permissions for AR
          const checkCameraPermissions = async () => {
            try {
              const permissions = await navigator.permissions.query({ name: 'camera' });
              console.log('Camera permission status:', permissions.state);
              return permissions.state;
            } catch (err) {
              console.log('Permission API not available:', err);
              return 'unknown';
            }
          };

          // Function to display artwork information
          const displayArtworkInfo = (artwork) => {
            const infoDiv = document.getElementById("artwork-info");
            const titleDiv = document.getElementById("artwork-title");
            const descDiv = document.getElementById("artwork-description");
            
            titleDiv.textContent = artwork.name;
            
            let infoHtml = "";
            if (artwork.artist) infoHtml += `<p><strong>Artist:</strong> ${artwork.artist}</p>`;
            if (artwork.artwork_type) infoHtml += `<p><strong>Type:</strong> ${artwork.artwork_type.charAt(0).toUpperCase() + artwork.artwork_type.slice(1)}</p>`;
            if (artwork.year_created) infoHtml += `<p><strong>Year Created:</strong> ${artwork.year_created}</p>`;
            if (artwork.medium) infoHtml += `<p><strong>Medium:</strong> ${artwork.medium}</p>`;
            if (artwork.dimensions) infoHtml += `<p><strong>Dimensions:</strong> ${artwork.dimensions}</p>`;
            if (artwork.style) infoHtml += `<p><strong>Style:</strong> ${artwork.style}</p>`;
            if (artwork.price) infoHtml += `<p><strong>Price:</strong> $${artwork.price.toFixed(2)}</p>`;
            if (artwork.description) infoHtml += `<p><strong>Description:</strong> ${artwork.description}</p>`;
            
            descDiv.innerHTML = infoHtml;
            infoDiv.style.display = "block";
          };
          
          document.getElementById("btn").onclick = async () => {
            const f = document.getElementById("file").files[0];
            const name = document.getElementById("name").value.trim();
            
            // Check network connectivity before proceeding
            if (!checkNetworkConnectivity()) {
              return;
            }
            
            if (!f) {
              showStatus("Please select an image first!", "error");
              return;
            }
            
            if (!name) {
              showStatus("Please enter an artwork name!", "error");
              return;
            }
            
            // Show loading state
            const btn = document.getElementById("btn");
            const originalText = btn.textContent;
            btn.textContent = "Processing...";
            btn.disabled = true;
            showStatus("Converting image to 3D model...", "info");
            
            // Check file size for mobile devices
            const maxSize = isMobile ? 5 * 1024 * 1024 : 10 * 1024 * 1024; // 5MB for mobile, 10MB for desktop
            if (f.size > maxSize) {
              const sizeMB = (f.size / (1024 * 1024)).toFixed(2);
              const maxSizeMB = (maxSize / (1024 * 1024)).toFixed(0);
              showStatus(`File too large (${sizeMB}MB). Maximum size for ${isMobile ? 'mobile' : 'desktop'} is ${maxSizeMB}MB.`, "error");
              btn.textContent = originalText;
              btn.disabled = false;
              return;
            }
            
            const fd = new FormData();
            fd.append("image", f);
            fd.append("name", name);
            fd.append("description", document.getElementById("description").value.trim());
            fd.append("price", document.getElementById("price").value.trim());
            fd.append("artwork_type", document.getElementById("artwork_type").value);
            fd.append("artist", document.getElementById("artist").value.trim());
            fd.append("year_created", document.getElementById("year_created").value.trim());
            fd.append("dimensions", document.getElementById("dimensions").value.trim());
            fd.append("medium", document.getElementById("medium").value.trim());
            fd.append("style", document.getElementById("style").value.trim());
            
            try {
              // Mobile-friendly fetch configuration with retry logic
              const maxRetries = 3;
              let retryCount = 0;
              
              const makeRequest = async () => {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s timeout for mobile
                
                // Add User-Agent and connection info for debugging
                const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
                const connectionType = navigator.connection ? navigator.connection.effectiveType : 'unknown';
                
                if (retryCount === 0) {
                  showStatus(`Processing on ${isMobile ? 'mobile' : 'desktop'} device (${connectionType} connection)...`, "info");
                } else {
                  showStatus(`Retrying upload (attempt ${retryCount + 1}/${maxRetries})...`, "info");
                }
                
                try {
                  // Send request to create artwork with mobile-optimized settings
                  const res = await fetch("/make-glb", { 
                    method: "POST", 
                    body: fd,
                    mode: 'cors',
                    credentials: 'omit',
                    signal: controller.signal,
                    headers: {
                      'Accept': 'application/json',
                      'X-Requested-With': 'XMLHttpRequest',
                      'X-Mobile-Request': isMobile ? 'true' : 'false',
                      'X-Connection-Type': connectionType,
                      'X-Retry-Count': retryCount.toString()
                    }
                  });
                  
                  clearTimeout(timeoutId);
                  
                  if (!res.ok) {
                    let errorMessage;
                    try {
                      const errorData = await res.json();
                      errorMessage = errorData.error || `Server error ${res.status}`;
                    } catch (parseError) {
                      const errorText = await res.text();
                      errorMessage = errorText || `Server error ${res.status}`;
                    }
                    console.error('Server response:', res.status, errorMessage);
                    throw new Error(errorMessage);
                  }
                  
                  return res;
                } catch (error) {
                  clearTimeout(timeoutId);
                  
                  // Check if it's a network error that could benefit from retry
                  const isNetworkError = error.name === 'AbortError' || 
                                       error.message.includes('fetch') || 
                                       error.message.includes('network') ||
                                       error.message.includes('Failed to fetch');
                  
                  if (isNetworkError && retryCount < maxRetries - 1) {
                    retryCount++;
                    console.log(`Retrying request (${retryCount}/${maxRetries}) due to:`, error.message);
                    // Wait a bit before retrying (exponential backoff)
                    await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, retryCount - 1)));
                    return makeRequest();
                  } else {
                    throw error;
                  }
                }
              };
              
              const res = await makeRequest();
              
              const result = await res.json();
              const artworkId = result.artwork_id;
              
              // Fetch artwork details from API endpoint (not HTML endpoint)
              const artworkRes = await fetch(`/api/artwork/${artworkId}`);
              if (!artworkRes.ok) {
                throw new Error(`Failed to fetch artwork details: ${artworkRes.status}`);
              }
              const artwork = await artworkRes.json();
              
              // Load the GLB file
              const glbUrl = `/artwork/${artworkId}/glb`;
              viewer.src = glbUrl;
              
              // Display artwork information
              displayArtworkInfo(artwork);
              
              // Show AR button once model is loaded
              viewer.addEventListener('load', function() {
                showStatus("3D model created successfully!", "success");
                arButton.style.display = "inline-block";
                arInstructions.style.display = "block";
                
                // Check for AR support
                if (!isARSupported()) {
                  showStatus("Warning: Your device may not support AR features", "error");
                }
              }, { once: true });
              
              viewer.addEventListener('error', function(error) {
                showStatus("Error loading 3D model: " + error, "error");
              });
              
            } catch (error) {
              console.error('Upload error:', error);
              
              // Provide mobile-specific error messages
              let errorMessage = error.message;
              
              if (error.name === 'AbortError') {
                errorMessage = "Upload timeout. Please check your internet connection and try again.";
              } else if (error.message.includes('Failed to fetch') || error.message.includes('network')) {
                errorMessage = "Network error. Please check your internet connection and try again.";
              } else if (error.message.includes('CORS')) {
                errorMessage = "Connection error. Please try refreshing the page.";
              } else if (error.message.includes('Unexpected token') && error.message.includes('JSON')) {
                errorMessage = "Server returned an unexpected response. This might be an authentication issue. Please try refreshing the page or logging in again.";
              } else if (error.message.includes('Failed to fetch artwork details')) {
                errorMessage = "Failed to load artwork information after upload. The artwork was created but details couldn't be retrieved.";
              }
              
              // Add mobile-specific debugging info
              const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
              if (isMobile) {
                console.log('Mobile device detected. Network info:', {
                  connection: navigator.connection ? {
                    effectiveType: navigator.connection.effectiveType,
                    downlink: navigator.connection.downlink,
                    rtt: navigator.connection.rtt
                  } : 'unavailable',
                  online: navigator.onLine,
                  userAgent: navigator.userAgent
                });
              }
              
              showStatus(errorMessage, "error");
            } finally {
              // Reset button state
              btn.textContent = originalText;
              btn.disabled = false;
            }
          };
          
          // Handle AR button click - Simple version that was working
          arButton.addEventListener('click', () => {
            if (!viewer.src) {
              showStatus("Please create a 3D model first!", "error");
              return;
            }

            showStatus("Launching AR viewer...", "info");
            
            try {
              // For local testing, allow without HTTPS check
              const isLocalhost = location.hostname.includes('localhost') || 
                                location.hostname.includes('127.0.0.1') || 
                                location.hostname.startsWith('192.168.');
              
              if (location.protocol !== 'https:' && !isLocalhost) {
                showStatus("AR requires HTTPS. Please use the deployed version on your mobile device.", "error");
                return;
              }
              
              // Disable scaling completely before AR activation
              viewer.setAttribute('ar-scale', 'fixed');
              viewer.disableZoom = true;
              viewer.disablePan = true;
              
              // Set fixed scale attributes
              viewer.setAttribute('min-camera-orbit', 'auto auto auto');
              viewer.setAttribute('max-camera-orbit', 'auto auto auto');
              viewer.setAttribute('min-field-of-view', 'auto');
              viewer.setAttribute('max-field-of-view', 'auto');
              
              // Simple AR activation - this was working in phone screen
              setTimeout(() => {
                viewer.activateAR();
              }, 500);
              
            } catch (error) {
              console.error("AR activation error:", error);
              showStatus("Error launching AR: " + error.message, "error");
            }
          });
          
          // Add debug info for AR support
          const debugInfo = document.createElement('div');
          debugInfo.style.fontSize = '12px';
          debugInfo.style.color = '#666';
          debugInfo.style.margin = '20px 0';
          debugInfo.style.textAlign = 'left';
          
          // Detect browser and AR capabilities
          const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
          const isAndroid = /Android/.test(navigator.userAgent);
          const isChrome = /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
          const hasWebXR = 'xr' in navigator && 'isSessionSupported' in navigator.xr;
          
          // Check Chrome version
          let chromeVersion = 'N/A';
          if (isChrome) {
            const match = navigator.userAgent.match(/Chrome\\/([0-9]+)/);
            if (match) {
              chromeVersion = match[1];
            }
          }
          
          // Check Android version
          let androidVersion = 'N/A';
          if (isAndroid) {
            const match = navigator.userAgent.match(/Android ([0-9]+)\\.([0-9]+)/);
            if (match) {
              androidVersion = `${match[1]}.${match[2]}`;
            }
          }
          
          debugInfo.innerHTML = `
            <details>
              <summary>Debug Information</summary>
              <p>User Agent: ${navigator.userAgent}</p>
              <p>Browser: ${isChrome ? 'Chrome ' + chromeVersion : isIOS ? 'Safari' : 'Other'}</p>
              <p>Platform: ${isAndroid ? 'Android ' + androidVersion : isIOS ? 'iOS' : 'Other'}</p>
              <p>WebXR Support: ${hasWebXR ? 'Yes' : 'No'}</p>
              <p>Protocol: ${location.protocol}</p>
              <p>Can Activate AR: ${viewer.canActivateAR ? 'Yes' : 'No'}</p>
              <p>AR Mode Priority: ${viewer.getAttribute('ar-modes')}</p>
              <p>Screen: ${window.innerWidth} x ${window.innerHeight}</p>
              <p>Secure Context: ${window.isSecureContext ? 'Yes' : 'No'}</p>
            </details>
          `;
          document.body.appendChild(debugInfo);
        }); // End DOMContentLoaded
        </script>
      </body>
    </html>
    """
    return Response(html, mimetype="text/html")

def _image_histogram_from_bytes(b, size=(64, 64)):
    try:
        img = Image.open(io.BytesIO(b)).convert("RGB").resize(size)
        return img.histogram()
    except Exception:
        return None

def _histogram_intersection(h1, h2):
    """Normalized intersection: sum(min(h1,h2)) / sum(h1). Returns 0..1."""
    if not h1 or not h2:
        return 0.0
    s1 = sum(h1)
    if s1 == 0:
        return 0.0
    inter = sum(min(a, b) for a, b in zip(h1, h2))
    return inter / s1

def _text_overlap_score(a_text, b_text):
    """Jaccard-like overlap on word tokens (0..1)."""
    if not a_text or not b_text:
        return 0.0
    a_words = set(re.findall(r"\w+", a_text.lower()))
    b_words = set(re.findall(r"\w+", b_text.lower()))
    if not a_words or not b_words:
        return 0.0
    return len(a_words & b_words) / len(a_words | b_words)

def recommend_similar_artworks(artwork, top_n=5):
    """
    Score candidates by:
      - exact metadata matches (artist, style, medium, type)
      - description word overlap
      - image histogram intersection
    Returns list of dicts with id, name, artist, and score.
    """
    candidates = Artwork.query.filter(Artwork.id != artwork.id).all()
    base_hist = _image_histogram_from_bytes(artwork.image_data)
    scored = []
    for c in candidates:
        score = 0.0
        # metadata matches (weighted)
        if artwork.artist and c.artist and artwork.artist == c.artist:
            score += 3.0
        if artwork.style and c.style and artwork.style == c.style:
            score += 2.0
        if artwork.medium and c.medium and artwork.medium == c.medium:
            score += 1.5
        if artwork.artwork_type and c.artwork_type and artwork.artwork_type == c.artwork_type:
            score += 1.0
        # description overlap
        score += _text_overlap_score(artwork.description, c.description) * 3.0
        # image histogram similarity
        c_hist = _image_histogram_from_bytes(c.image_data)
        hist_sim = _histogram_intersection(base_hist, c_hist)
        score += hist_sim * 3.0
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for s, art in scored[:top_n]:
        results.append({
            "id": art.id,
            "name": art.name,
            "artist": art.artist,
            "style": art.style,
            "medium": art.medium,
            "score": round(s, 4)
        })
    return results

@app.route("/api/artwork/<int:artwork_id>/recommendations", methods=["GET"])
def artwork_recommendations(artwork_id):
    """Return JSON list of recommended artworks similar to artwork_id."""
    art = Artwork.query.get_or_404(artwork_id)
    recs = recommend_similar_artworks(art, top_n=6)
    return jsonify({"artwork_id": artwork_id, "recommendations": recs})

def _artworks_query_for_user(user):
    """Return a SQLAlchemy Query for Artwork filtered to items uploaded by `user`.
    Tries common uploader column names (user_id, owner_id, uploader_id, created_by, creator_id)
    and falls back to returning all if no uploader column exists.
    """
    q = Artwork.query
    if user is None:
        # not logged in -> no results
        return q.filter(False)

    # detect uploader-like column names on the model
    try:
        cols = {c.name for c in Artwork.__table__.columns}
    except Exception:
        cols = set()

    for col in ("user_id", "owner_id", "uploader_id", "created_by", "creator_id"):
        if col in cols:
            return q.filter(getattr(Artwork, col) == user.id)

    # try relationship attributes (Artwork.user or Artwork.owner)
    if hasattr(Artwork, "user"):
        return q.filter(Artwork.user == user)
    if hasattr(Artwork, "owner"):
        return q.filter(Artwork.owner == user)

 # ...existing code...
    # No uploader info found: log and return all (you may want to change this to deny)
    app.logger.info("No uploader column found on Artwork; admin view will show all artworks")
    return q
# ...existing code...

@app.route("/admin")
@login_required
def admin_page():
    user = get_current_user()

    # Replace any broad query like: artworks = Artwork.query.order_by(...).all()
    # with the filtered query below so users only see their own uploads.
    artworks = _artworks_query_for_user(user).order_by(Artwork.created_at.desc()).all()

    # ...existing code that renders the admin page using `artworks` ...
    # Example: return render_template_string(..., artworks=artworks)
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin - AR Art Gallery</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f4f4f9; }
            h1 { font-size: 24px; color: #333; margin: 20px; }
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
            th, td { padding: 12px; text-align: left; border: 1px solid #ddd; }
            th { background: #007bff; color: white; }
            tr:hover { background: #f1f1f1; }
            .btn { display: inline-block; padding: 10px 20px; margin: 10px 0; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
            .btn:hover { background: #0056b3; }
            .success { color: #28a745; }
            .error { color: #dc3545; }
            .info { color: #17a2b8; }
            @media (max-width: 768px) {
                table, thead, tbody, th, td, tr { display: block; width: 100%; }
                th { display: none; }
                tr { margin-bottom: 10px; border: 1px solid #ddd; }
                td { text-align: right; padding-left: 50%; position: relative; }
                td:before {
                    content: attr(data-label);
                    position: absolute;
                    left: 10px;
                    width: calc(50% - 20px);
                    padding-right: 10px;
                    text-align: left;
                    font-weight: bold;
                    color: #333;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛠️ Admin Panel - Manage Artworks</h1>
            
            <div id="status"></div>
            
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Artist</th>
                        <th>Type</th>
                        <th>Style</th>
                        <th>Medium</th>
                        <th>Dimensions</th>
                        <th>Year</th>
                        <th>Price</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for artwork in artworks %}
                    <tr>
                        <td data-label="ID">{{ artwork.id }}</td>
                        <td data-label="Name">{{ artwork.name }}</td>
                        <td data-label="Artist">{{ artwork.artist or 'N/A' }}</td>
                        <td data-label="Type">{{ artwork.artwork_type or 'N/A' }}</td>
                        <td data-label="Style">{{ artwork.style or 'N/A' }}</td>
                        <td data-label="Medium">{{ artwork.medium or 'N/A' }}</td>
                        <td data-label="Dimensions">{{ artwork.dimensions or 'N/A' }}</td>
                        <td data-label="Year">{{ artwork.year_created or 'N/A' }}</td>
                        <td data-label="Price">${{ "%.2f"|format(artwork.price) if artwork.price else 'N/A' }}</td>
                        <td data-label="Actions">
                            <a href="/artwork/{{ artwork.id }}/image" class="btn" target="_blank">View Image</a>
                            <a href="/artwork/{{ artwork.id }}/glb" class="btn" target="_blank">Download GLB</a>
                            <a href="javascript:void(0);" class="btn delete-btn" data-id="{{ artwork.id }}">Delete</a>
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="10" style="text-align: center; padding: 20px;">No artworks found. Upload new artworks to display here.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            <h2>Upload New Artwork</h2>
            <form id="uploadForm" enctype="multipart/form-data">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div>
                        <label for="name">Artwork Name *</label>
                        <input type="text" id="name" name="name" required>
                    </div>
                    <div>
                        <label for="artist">Artist</label>
                        <input type="text" id="artist" name="artist">
                    </div>
                    <div>
                        <label for="price">Price ($)</label>
                        <input type="number" id="price" name="price" step="0.01">
                    </div>
                    <div>
                        <label for="artwork_type">Type</label>
                        <input type="text" id="artwork_type" name="artwork_type">
                    </div>
                    <div>
                        <label for="year_created">Year Created</label>
                        <input type="number" id="year_created" name="year_created">
                    </div>
                    <div>
                        <label for="dimensions">Dimensions</label>
                        <input type="text" id="dimensions" name="dimensions">
                    </div>
                    <div>
                        <label for="medium">Medium</label>
                        <input type="text" id="medium" name="medium">
                    </div>
                    <div>
                        <label for="style">Style</label>
                        <input type="text" id="style" name="style">
                    </div>
                    <div>
                        <label for="description">Description</label>
                        <textarea id="description" name="description" rows="3"></textarea>
                    </div>
                    <div>
                        <label for="image">Image File *</label>
                        <input type="file" id="image" name="image" accept="image/*" required>
                    </div>
                </div>
                <button type="submit" style="margin-top: 15px;">Upload Artwork</button>
            </form>
        </div>
        
        <script>
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const statusDiv = document.getElementById('status');
            
            // Clear previous status messages
            statusDiv.innerHTML = '';
            
            try {
                const response = await fetch('/make-glb', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    statusDiv.innerHTML = '<p class="success">Artwork uploaded successfully!</p>';
                    
                    // Optionally, refresh the page or update the artworks table
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    statusDiv.innerHTML = `<p class="error">Error: ${result.error}</p>`;
                }
            } catch (error) {
                statusDiv.innerHTML = `<p class="error">Unexpected error: ${error.message}</p>`;
            }
        });
        
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const artworkId = this.getAttribute('data-id');
                if (confirm('Are you sure you want to delete this artwork?')) {
                    fetch(`/api/artwork/${artworkId}`, {
                        method: 'DELETE'
                    })
                    .then(response => response.json())
                    .then(result => {
                        if (result.success) {
                            alert('Artwork deleted successfully!');
                            window.location.reload();
                        } else {
                            alert('Error deleting artwork: ' + result.error);
                        }
                    })
                    .catch(error => {
                        alert('Unexpected error: ' + error.message);
                    });
                }
            });
        });
        </script>
    </body>
    </html>
    """, artworks=artworks)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "true").lower() in ("1", "true", "yes"))
