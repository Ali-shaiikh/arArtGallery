import io
import numpy as np
import trimesh
from PIL import Image
from flask import Blueprint, request, send_file, abort, Response, jsonify
from datetime import datetime

from .extensions import db
from .models import Artwork
from .recommendations import recommend_similar_artworks

artworks_bp = Blueprint("artworks", __name__)

def create_glb_from_image(file_like, width_m=0.6, thickness_m=0.01):
    try:
        img = Image.open(file_like).convert("RGB")

        from PIL import ImageEnhance
        img = ImageEnhance.Contrast(img).enhance(1.2)
        img = ImageEnhance.Color(img).enhance(1.1)

        w_px, h_px = img.size
        if w_px == 0 or h_px == 0:
            raise ValueError("Invalid image dimensions")

        aspect = h_px / float(w_px)

        W = float(width_m)
        H = W * aspect
        T = float(thickness_m)

        box = trimesh.creation.box(extents=(W, H, T))
        box.apply_translation((0, 0, T / 2.0))

        uv = np.zeros((len(box.vertices), 2), dtype=np.float32)
        verts = box.vertices
        min_xy = verts[:, :2].min(axis=0)
        max_xy = verts[:, :2].max(axis=0)
        span_xy = np.maximum(max_xy - min_xy, 1e-8)
        uv[:] = (verts[:, :2] - min_xy) / span_xy

        texture = trimesh.visual.texture.TextureVisuals(uv=uv, image=img)
        box.visual = texture

        glb_bytes = box.export(file_type="glb")
        return glb_bytes if isinstance(glb_bytes, bytes) else glb_bytes.read()

    except Exception as e:
        print(f"Error in create_glb_from_image: {str(e)}")
        return None

@artworks_bp.route("/health", methods=["GET", "OPTIONS"])
def health_check():
    if request.method == "OPTIONS":
        response = Response(status=200)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept, X-Mobile-Request"
        return response

    is_mobile = request.headers.get("X-Mobile-Request", "false") == "true"
    user_agent = request.headers.get("User-Agent", "unknown")

    health_info = {
        "status": "OK",
        "timestamp": datetime.now().isoformat(),
        "mobile_detected": is_mobile,
        "user_agent": user_agent[:100]
    }

    if request.headers.get("Accept", "").startswith("application/json"):
        return jsonify(health_info)
    return Response(f"OK - Mobile: {is_mobile}", status=200, mimetype="text/plain")

@artworks_bp.route("/make-glb", methods=["POST", "OPTIONS"])
def make_glb():
    if request.method == "OPTIONS":
        response = Response(status=200)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept, Authorization, X-Requested-With, Origin, X-Mobile-Request, X-Connection-Type, X-Retry-Count"
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Access-Control-Allow-Credentials"] = "false"
        response.headers["Content-Length"] = "0"
        return response

    try:
        if "image" not in request.files:
            return Response(
                '{"success": false, "error": "No file uploaded. Please select an image file."}',
                mimetype="application/json",
                status=400,
            )

        f = request.files["image"]
        if f.filename == "":
            return Response(
                '{"success": false, "error": "No file selected. Please choose an image."}',
                mimetype="application/json",
                status=400,
            )

        if not f.content_type or not f.content_type.startswith("image/"):
            return Response(
                '{"success": false, "error": "Invalid file type. Please upload an image file (JPG, PNG, etc.)."}',
                mimetype="application/json",
                status=400,
            )

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price_str = request.form.get("price", "").strip()
        artwork_type = request.form.get("artwork_type", "").strip()
        artist = request.form.get("artist", "").strip()
        year_created_str = request.form.get("year_created", "").strip()
        dimensions = request.form.get("dimensions", "").strip()
        medium = request.form.get("medium", "").strip()
        style = request.form.get("style", "").strip()

        if not name:
            return Response(
                '{"success": false, "error": "Artwork name is required."}',
                mimetype="application/json",
                status=400,
            )

        price = float(price_str) if price_str else None
        year_created = int(year_created_str) if year_created_str else None

        image_data = f.read()
        glb_bytes = create_glb_from_image(io.BytesIO(image_data))

        if not glb_bytes:
            return Response(
                '{"success": false, "error": "Failed to process image. Please try a different image."}',
                mimetype="application/json",
                status=500,
            )

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
            filename=f.filename,
        )

        db.session.add(artwork)
        db.session.commit()

        return Response(
            f'{{"success": true, "artwork_id": {artwork.id}}}',
            mimetype="application/json",
            status=200,
        )

    except Exception as e:
        db.session.rollback()
        return Response(
            f'{{"success": false, "error": "Server error while processing image: {str(e)}"}}',
            mimetype="application/json",
            status=500,
        )

@artworks_bp.route("/artwork/<int:artwork_id>/image")
def artwork_image(artwork_id):
    art = Artwork.query.get_or_404(artwork_id)
    img_bytes = getattr(art, "image_data", None) or getattr(art, "image", None)
    if not img_bytes:
        abort(404, "Image not found")
    return send_file(io.BytesIO(img_bytes), mimetype="image/png", download_name=f"artwork-{artwork_id}.png")

@artworks_bp.route("/artwork/<int:artwork_id>/glb")
def artwork_glb(artwork_id):
    art = Artwork.query.get_or_404(artwork_id)
    glb_bytes = getattr(art, "glb_data", None) or getattr(art, "glb", None)
    if not glb_bytes:
        abort(404, "GLB not found")
    return send_file(io.BytesIO(glb_bytes), mimetype="model/gltf-binary", download_name=f"artwork-{artwork_id}.glb")

@artworks_bp.route("/api/artwork/<int:artwork_id>", methods=["GET"])
def get_artwork_api(artwork_id):
    artwork = Artwork.query.get_or_404(artwork_id)
    return jsonify({
        "id": artwork.id,
        "name": artwork.name,
        "description": artwork.description,
        "price": artwork.price,
        "artwork_type": artwork.artwork_type,
        "artist": artwork.artist,
        "year_created": artwork.year_created,
        "dimensions": artwork.dimensions,
        "medium": artwork.medium,
        "style": artwork.style,
        "created_at": artwork.created_at.isoformat() if artwork.created_at else None,
        "filename": artwork.filename,
    })

@artworks_bp.route("/artworks", methods=["GET"])
def list_artworks():
    artworks = Artwork.query.order_by(Artwork.created_at.desc()).all()
    data = []
    for a in artworks:
        data.append({
            "id": a.id,
            "name": a.name,
            "artist": a.artist,
            "artwork_type": a.artwork_type,
            "price": a.price,
            "description": a.description,
            "year_created": a.year_created,
            "dimensions": a.dimensions,
            "medium": a.medium,
            "style": a.style,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return jsonify(data)

@artworks_bp.route("/api/artwork/<int:artwork_id>", methods=["PUT"])
def update_artwork(artwork_id):
    try:
        artwork = Artwork.query.get_or_404(artwork_id)
        data = request.get_json() or {}

        if "name" in data:
            artwork.name = data["name"].strip()
        if "description" in data:
            artwork.description = data["description"].strip()
        if "price" in data:
            artwork.price = float(data["price"]) if data["price"] else None
        if "artwork_type" in data:
            artwork.artwork_type = data["artwork_type"].strip()
        if "artist" in data:
            artwork.artist = data["artist"].strip()
        if "year_created" in data:
            artwork.year_created = int(data["year_created"]) if data["year_created"] else None
        if "dimensions" in data:
            artwork.dimensions = data["dimensions"].strip()
        if "medium" in data:
            artwork.medium = data["medium"].strip()
        if "style" in data:
            artwork.style = data["style"].strip()

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Artwork updated successfully",
            "artwork": {
                "id": artwork.id,
                "name": artwork.name,
                "description": artwork.description,
                "price": artwork.price,
                "artwork_type": artwork.artwork_type,
                "artist": artwork.artist,
                "year_created": artwork.year_created,
                "dimensions": artwork.dimensions,
                "medium": artwork.medium,
                "style": artwork.style,
                "created_at": artwork.created_at.isoformat(),
                "filename": artwork.filename,
            },
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@artworks_bp.route("/api/artwork/<int:artwork_id>", methods=["DELETE"])
def delete_artwork(artwork_id):
    try:
        artwork = Artwork.query.get_or_404(artwork_id)
        artwork_name = artwork.name

        db.session.delete(artwork)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f'Artwork "{artwork_name}" deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@artworks_bp.route("/api/artwork/<int:artwork_id>/recommendations", methods=["GET"])
def artwork_recommendations(artwork_id):
    art = Artwork.query.get_or_404(artwork_id)
    recs = recommend_similar_artworks(art, top_n=6)
    return jsonify({"artwork_id": artwork_id, "recommendations": recs})
