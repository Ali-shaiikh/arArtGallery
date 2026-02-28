#!/usr/bin/env python3
"""
Database initialization script for AR Module
Run this to create the database tables if they don't exist
"""

from app import app, db

def init_db():
    """Initialize the database"""
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created successfully!")
        
        # Check if tables exist
        from app import Artwork, User
        artwork_count = Artwork.query.count()
        user_count = User.query.count()
        
        print(f"📊 Current data:")
        print(f"   Artworks: {artwork_count}")
        print(f"   Users: {user_count}")

if __name__ == "__main__":
    init_db()