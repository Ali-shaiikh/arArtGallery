from flask import Flask
from .config import Config
from .extensions import db, cors



def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # init extensions
    db.init_app(app)

    cors.init_app(
        app,
        supports_credentials=True,
        resources={
            r"/*": {
                "origins": [
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                ],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "Cache-Control",
                    "X-Requested-With",
                    "X-Mobile-Request",
                    "X-Connection-Type",
                    "X-Retry-Count",
                ],
            }
        },
    )

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
