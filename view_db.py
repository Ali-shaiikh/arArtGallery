#!/usr/bin/env python3
"""
Database Viewer for AR Module
Run this script to view all artwork data in the database
"""

import sqlite3
from datetime import datetime

def view_database():
    # Connect to the database
    conn = sqlite3.connect('artwork.db')
    cursor = conn.cursor()

    # Get all artwork records
    cursor.execute('SELECT * FROM artwork')
    rows = cursor.fetchall()

    # Get column names
    cursor.execute('PRAGMA table_info(artwork)')
    columns = [col[1] for col in cursor.fetchall()]

    print("🎨 AR MODULE DATABASE VIEWER")
    print("=" * 50)
    print(f"Total artworks: {len(rows)}")
    print()

    for i, row in enumerate(rows, 1):
        print(f"🏛️  ARTWORK #{i}")
        print("-" * 30)

        for j, col in enumerate(columns):
            value = row[j]

            # Format the output nicely
            if col == 'price' and value:
                print(f"{col.title()}: ${value}")
            elif col == 'created_at' and value:
                # Parse and format datetime
                try:
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    print(f"{col.title()}: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    print(f"{col.title()}: {value}")
            elif col in ['image_data', 'glb_data']:
                # Don't print binary data
                print(f"{col.title()}: [Binary data - {len(value) if value else 0} bytes]")
            else:
                print(f"{col.title()}: {value if value else 'Not specified'}")

        print()

    conn.close()

if __name__ == "__main__":
    view_database()