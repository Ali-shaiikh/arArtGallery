from flask import Flask
from .config import Config
from .extensions import db, cors

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # init extensions
    db.init_app(app)
    cors.init_app(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Content-Type",
                "Authorization",
                "Access-Control-Allow-Credentials",
                "Cache-Control",
                "X-Requested-With",
                "X-Mobile-Request",
                "X-Connection-Type",
                "X-Retry-Count"
            ]
        }
    })

    # add headers (same as your app.py)
    @app.after_request
    def add_header(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept, Authorization, X-Requested-With, Origin, X-Mobile-Request, X-Connection-Type, X-Retry-Count"
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Access-Control-Allow-Credentials"] = "false"

        response.headers.pop("Cross-Origin-Opener-Policy", None)
        response.headers.pop("Cross-Origin-Embedder-Policy", None)
        response.headers.pop("Cross-Origin-Resource-Policy", None)
        return response

    # import + register blueprints
    from .spa import spa_bp
    from .auth import auth_bp
    from .artworks import artworks_bp
    from .admin import admin_bp

    app.register_blueprint(spa_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(artworks_bp)
    app.register_blueprint(admin_bp)

    # create tables
    with app.app_context():
        db.create_all()

    return app
