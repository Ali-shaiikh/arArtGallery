import os
from flask import Blueprint, request, jsonify, render_template_string

from .models import Artwork
from .auth import login_required, get_current_user
from .config import basedir

admin_bp = Blueprint("admin", __name__)


# ---------------------------
# Helper: Filter artworks by user (best-effort)
# ---------------------------
def _artworks_query_for_user(user):
    """
    Return a SQLAlchemy Query for Artwork filtered to items uploaded by `user`.
    Tries common uploader column names (user_id, owner_id, uploader_id, created_by, creator_id)
    and falls back to returning all if no uploader column exists.
    """
    q = Artwork.query

    if user is None:
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

    # No uploader info found: return all
    return q


# ---------------------------
# /admin/populate
# ---------------------------
@admin_bp.route("/admin/populate", methods=["GET", "POST"])
def populate_gallery():
    if request.method == "GET":
        # Count existing artworks and images in data folder
        artwork_count = Artwork.query.count()

        data_folder = os.path.join(basedir, "data")
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}
        image_count = 0

        if os.path.exists(data_folder):
            for filename in os.listdir(data_folder):
                if os.path.isfile(os.path.join(data_folder, filename)):
                    _, ext = os.path.splitext(filename.lower())
                    if ext in image_extensions:
                        image_count += 1

        return render_template_string(
            """
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
        """,
            artwork_count=artwork_count,
            image_count=image_count,
        )

    # POST
    try:
        gemini_api_key = request.form.get("gemini_api_key", "").strip()

        # Import the populator
        from .populate_artworks import ArtworkPopulator

        populator = ArtworkPopulator(gemini_api_key if gemini_api_key else None)
        data_folder = os.path.join(basedir, "data")

        # Count images before processing
        initial_count = Artwork.query.count()

        # Process images
        populator.populate_from_folder(data_folder)

        # Count images after processing
        final_count = Artwork.query.count()
        processed = final_count - initial_count

        return jsonify({"success": True, "processed": processed, "total_artworks": final_count})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------
# /database
# ---------------------------
@admin_bp.route("/database")
def view_database():
    artworks = Artwork.query.all()
    return render_template_string(
        """
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
    """,
        artworks=artworks,
    )


# ---------------------------
# /admin
# ---------------------------
@admin_bp.route("/admin")
@login_required
def admin_page():
    user = get_current_user()
    artworks = _artworks_query_for_user(user).order_by(Artwork.created_at.desc()).all()

    return render_template_string(
        """
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
        input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { background: #4CAF50; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #45a049; }

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
                    <td colspan="10" style="text-align: center; padding: 20px;">
                        No artworks found. Upload new artworks to display here.
                    </td>
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

                // Refresh the page
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
    """,
        artworks=artworks,
    )
