from datetime import datetime
from .extensions import db

class Artwork(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user = db.relationship("User", backref="artworks")

    name = db.Column(db.String(200), nullable=False, default="Untitled Artwork")
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=True)
    artwork_type = db.Column(db.String(50), nullable=True)
    artist = db.Column(db.String(200), nullable=True)
    year_created = db.Column(db.Integer, nullable=True)
    dimensions = db.Column(db.String(100), nullable=True)
    medium = db.Column(db.String(100), nullable=True)
    style = db.Column(db.String(100), nullable=True)
    image_data = db.Column(db.LargeBinary, nullable=False)
    glb_data = db.Column(db.LargeBinary, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    filename = db.Column(db.String(200), nullable=False)

    is_sold = db.Column(db.Boolean, default=False)


   


    def __repr__(self):
        return f"<Artwork {self.name}>"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.name} ({self.email})>"
