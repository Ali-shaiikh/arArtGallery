import io
import re
from PIL import Image
from .models import Artwork

def _image_histogram_from_bytes(b, size=(64, 64)):
    try:
        img = Image.open(io.BytesIO(b)).convert("RGB").resize(size)
        return img.histogram()
    except Exception:
        return None

def _histogram_intersection(h1, h2):
    if not h1 or not h2:
        return 0.0
    s1 = sum(h1)
    if s1 == 0:
        return 0.0
    inter = sum(min(a, b) for a, b in zip(h1, h2))
    return inter / s1

def _text_overlap_score(a_text, b_text):
    if not a_text or not b_text:
        return 0.0
    a_words = set(re.findall(r"\w+", a_text.lower()))
    b_words = set(re.findall(r"\w+", b_text.lower()))
    if not a_words or not b_words:
        return 0.0
    return len(a_words & b_words) / len(a_words | b_words)

def recommend_similar_artworks(artwork, top_n=5):
    candidates = Artwork.query.filter(Artwork.id != artwork.id).all()
    base_hist = _image_histogram_from_bytes(artwork.image_data)

    scored = []
    for c in candidates:
        score = 0.0

        if artwork.artist and c.artist and artwork.artist == c.artist:
            score += 3.0
        if artwork.style and c.style and artwork.style == c.style:
            score += 2.0
        if artwork.medium and c.medium and artwork.medium == c.medium:
            score += 1.5
        if artwork.artwork_type and c.artwork_type and artwork.artwork_type == c.artwork_type:
            score += 1.0

        score += _text_overlap_score(artwork.description, c.description) * 3.0

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
