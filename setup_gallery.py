#!/usr/bin/env python3
"""
Quick Setup Script for AR Gallery Artwork Population
This script helps you set up your artwork images and populate the gallery
"""

import os
import shutil
from pathlib import Path

def create_sample_data_structure():
    """Create the data folder structure and example files"""
    
    # Create data folder if it doesn't exist
    data_folder = Path("data")
    data_folder.mkdir(exist_ok=True)
    
    # Create a README in the data folder
    readme_content = """# Artwork Images Folder

Place your artwork images in this folder to automatically populate the AR gallery.

## Supported Formats:
- JPG/JPEG
- PNG
- GIF
- BMP
- WEBP
- TIFF

## File Naming Tips:
- Use descriptive names (e.g., "sunset_landscape.jpg", "abstract_blue.png")
- The filename will be used to generate the artwork title
- Underscores and hyphens will be converted to spaces

## To Populate the Gallery:
1. Add your artwork images to this folder
2. Run: `python populate_artworks.py`
3. Enter your Gemini API key for AI-generated descriptions (optional)
4. The script will process all images and add them to the gallery

## Example Images:
You can find free artwork images at:
- Unsplash.com (search for "paintings", "art", "abstract")
- Pexels.com (search for "artwork", "canvas", "gallery")
- Public domain art collections

Make sure you have rights to use any images you add!
"""
    
    with open(data_folder / "README.md", "w") as f:
        f.write(readme_content)
    
    print(f"✅ Created data folder: {data_folder.absolute()}")
    print("📖 Added README.md with instructions")
    
    return data_folder

def show_instructions():
    """Show setup instructions to the user"""
    
    print("🎨 AR Gallery Artwork Setup")
    print("=" * 50)
    print()
    
    # Create data folder
    data_folder = create_sample_data_structure()
    
    print("📋 SETUP INSTRUCTIONS:")
    print()
    print("1. 📁 Add artwork images to the 'data' folder")
    print("   - Supported formats: JPG, PNG, GIF, BMP, WEBP, TIFF")
    print("   - Use descriptive filenames")
    print()
    
    print("2. 🔑 Get a Gemini API key (optional but recommended):")
    print("   - Go to: https://makersuite.google.com/app/apikey")
    print("   - Create a new API key")
    print("   - This will generate beautiful AI descriptions for your artworks")
    print()
    
    print("3. 🏃 Run the population script:")
    print("   python populate_artworks.py")
    print()
    
    print("4. 🌐 Start your server and check the buyer page:")
    print("   python app.py")
    print("   Visit: http://127.0.0.1:7861/buyer")
    print()
    
    print("🎯 QUICK START:")
    print("If you want to test immediately, add some artwork images to the 'data' folder")
    print("and run 'python populate_artworks.py' - it works without the API key too!")
    print()
    
    # Check if data folder has images
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
    image_count = 0
    
    if data_folder.exists():
        for file in data_folder.iterdir():
            if file.is_file() and file.suffix.lower() in image_extensions:
                image_count += 1
    
    if image_count > 0:
        print(f"🖼️  Found {image_count} image(s) in data folder!")
        print("Ready to run: python populate_artworks.py")
    else:
        print("📥 No images found in data folder yet.")
        print("Add some artwork images and then run the population script!")
    
    print()
    print("=" * 50)

if __name__ == "__main__":
    show_instructions()