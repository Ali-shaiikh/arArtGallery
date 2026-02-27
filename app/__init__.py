from flask import Flask, request
from .config import Config
from .extensions import db, cors



def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # init extensions
    db.init_app(app)

    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:5001",
    ]

    cors.init_app(
        app,
        origins=allowed_origins,
        supports_credentials=True,
        resources={
            r"/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "Access-Control-Allow-Credentials",
                    "Cache-Control",
                    "X-Requested-With",
                    "X-Mobile-Request",
                    "X-Connection-Type",
                    "X-Retry-Count",
                ],
            }
        },
    )

    @app.after_request
    def add_header(response):
        origin = request.headers.get("Origin")
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept, Authorization, X-Requested-With, Origin, X-Mobile-Request, X-Connection-Type, X-Retry-Count"
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers.pop("Cross-Origin-Opener-Policy", None)
        response.headers.pop("Cross-Origin-Embedder-Policy", None)
        response.headers.pop("Cross-Origin-Resource-Policy", None)
        return response

    # import + register blueprints
    from .spa import spa_bp
    from .auth import auth_bp
    from .artworks import artworks_bp
    from .admin import admin_bp
    from .payments import payments_bp


    app.register_blueprint(spa_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(artworks_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(payments_bp)



    # create tables
    with app.app_context():
        db.create_all()

    return app
