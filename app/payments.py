import os
import hmac
import hashlib
import razorpay

from flask import Blueprint, request, jsonify
from .extensions import db
from .models import Artwork
from .auth import get_current_user   # 👈 important

payments_bp = Blueprint("payments", __name__)

def get_razorpay_client():
    key_id = os.environ.get("RAZORPAY_KEY_ID")
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret:
        raise Exception("Razorpay keys missing. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env")

    return razorpay.Client(auth=(key_id, key_secret))

# ✅ 1) Create Order
# ✅ 1) Create Order (single artwork)
@payments_bp.route("/api/create-order", methods=["POST"])
def create_order():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "error": "Not authenticated"}), 401

    data = request.get_json() or {}

    artwork_id = data.get("artwork_id")
    if not artwork_id:
        return jsonify({"success": False, "error": "artwork_id is required"}), 400

    artwork = Artwork.query.get(artwork_id)
    if not artwork:
        return jsonify({"success": False, "error": "Artwork not found"}), 404

    if artwork.is_sold:
        return jsonify({"success": False, "error": "Artwork already sold"}), 400

    if artwork.price is None or float(artwork.price) <= 0:
        return jsonify({"success": False, "error": "Artwork has no valid price"}), 400

    amount_in_paise = int(float(artwork.price) * 100)

    client = razorpay.Client(auth=(
        os.environ.get("RAZORPAY_KEY_ID"),
        os.environ.get("RAZORPAY_KEY_SECRET")
    ))

    order = client.order.create({
        "amount": amount_in_paise,
        "currency": "INR",
        "payment_capture": 1,
        "notes": {
            "buyer_id": str(user.id),
            "artwork_id": str(artwork.id),
        }
    })

    return jsonify({
        "success": True,
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key_id": os.environ.get("RAZORPAY_KEY_ID"),
    })




@payments_bp.route("/api/verify-payment", methods=["POST"])
def verify_payment():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "error": "Not authenticated"}), 401

    data = request.get_json() or {}

    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")
    artwork_id = data.get("artwork_id")

    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature or not artwork_id:
        return jsonify({"success": False, "error": "Missing payment verification fields"}), 400

    artwork = Artwork.query.get(artwork_id)
    if not artwork:
        return jsonify({"success": False, "error": "Artwork not found"}), 404

    if artwork.is_sold:
        return jsonify({"success": False, "error": "Artwork already sold"}), 400

    key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    if not key_secret:
        return jsonify({"success": False, "error": "Razorpay secret missing in env"}), 500

    payload = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected_signature = hmac.new(
        key_secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    if expected_signature != razorpay_signature:
        return jsonify({"success": False, "error": "Payment verification failed"}), 400

    # ✅ Mark artwork sold
    artwork.is_sold = True
    db.session.commit()

    return jsonify({"success": True, "message": "Payment verified, artwork marked as sold"})
