import os

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "artwork.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Keep for SPA paths
    BASEDIR = basedir
