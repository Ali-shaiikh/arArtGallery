"""
Automatic Artwork Populator for AR Gallery
Processes images from data folder and adds them to the database with AI-generated descriptions
"""

import os
import io
import random
from PIL import Image
import requests

from .models import Artwork
from .extensions import db
from .artworks import create_glb_from_image
from . import create_app


class ArtworkPopulator:
    def __init__(self, gemini_api_key=None):
        self.gemini_api_key = gemini_api_key
        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

        # Realistic artwork metadata for random generation
        self.artists = [
            "Vincent van Gogh", "Pablo Picasso", "Leonardo da Vinci", "Claude Monet",
            "Salvador Dalí", "Frida Kahlo", "Jackson Pollock", "Georgia O'Keeffe",
            "Henri Matisse", "Andy Warhol", "Wassily Kandinsky", "Paul Cézanne",
            "Edvard Munch", "Gustav Klimt", "Johannes Vermeer", "Rembrandt van Rijn",
            "Edgar Degas", "Pierre-Auguste Renoir", "Caravaggio", "Banksy",
            "Jean-Michel Basquiat", "Keith Haring", "Roy Lichtenstein", "Mark Rothko",
            "Willem de Kooning", "David Hockney", "Yves Klein", "Kazimir Malevich"
        ]

        self.artwork_types = ["painting", "sculpture", "digital", "photography", "print", "mixed_media"]

        self.mediums = [
            "oil", "acrylic", "watercolor", "gouache", "pastel", "charcoal",
            "pencil", "ink", "mixed_media", "photography", "digital", "printmaking"
        ]

        self.styles = [
            "abstract", "realistic", "impressionist", "expressionist", "surrealist",
            "cubist", "minimalist", "pop_art", "street_art", "contemporary",
            "modern", "classical", "renaissance", "baroque"
        ]

        self.dimensions = [
            "8x10 inches", "11x14 inches", "16x20 inches", "18x24 inches",
            "20x24 inches", "24x30 inches", "24x36 inches", "30x40 inches",
            "36x48 inches", "40x60 inches", "48x72 inches"
        ]

    def generate_description_with_ai(self, artwork_name, artist, style, medium, artwork_type):
        """Generate artwork description using Gemini AI"""
        if not self.gemini_api_key:
            return self.generate_fallback_description(artwork_name, artist, style, medium, artwork_type)

        prompt = f"""Generate a compelling and artistic description for an artwork with these details:

Title: {artwork_name}
Artist: {artist}
Style: {style}
Medium: {medium}
Type: {artwork_type}

Write a 2-3 sentence description that captures the essence, mood, and artistic significance of this piece.
Make it sound professional and engaging for an art gallery. Focus on visual elements, emotional impact,
and artistic technique. Do not mention the price or commercial aspects."""

        try:
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }

            response = requests.post(
                f"{self.gemini_url}?key={self.gemini_api_key}",
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    description = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return description

            # fallback
            return self.generate_fallback_description(artwork_name, artist, style, medium, artwork_type)

        except Exception:
            return self.generate_fallback_description(artwork_name, artist, style, medium, artwork_type)

    def generate_fallback_description(self, artwork_name, artist, style, medium, artwork_type):
        """Generate a fallback description without AI"""
        descriptions = [
            f"A captivating {style} {artwork_type} that showcases {artist}'s mastery of {medium}. The composition draws viewers into a world of emotion and artistic expression.",
            f"This {style} piece demonstrates exceptional technique in {medium}, creating a powerful visual narrative that resonates with contemporary audiences.",
            f"An extraordinary example of {style} art, this {artwork_type} combines traditional {medium} techniques with innovative artistic vision.",
            f"A mesmerizing work that captures the essence of {style} movement through skillful use of {medium} and compelling visual storytelling.",
            f"This remarkable {artwork_type} showcases the artist's unique interpretation of {style} aesthetics through masterful {medium} application."
        ]
        return random.choice(descriptions)

    def generate_artwork_metadata(self, filename):
        """Generate random but realistic artwork metadata"""
        base_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()

        creative_prefixes = [
            "Symphony of", "Whispers of", "Dance of", "Dreams of", "Echoes of",
            "Meditation on", "Study in", "Variations on", "Homage to", "Spirit of"
        ]

        creative_suffixes = [
            "at Dawn", "in Blue", "at Twilight", "in Motion", "Remembered",
            "Eternal", "Awakening", "Transcendent", "Infinite", "Sublime"
        ]

        if random.choice([True, False]):
            if random.choice([True, False]):
                artwork_name = f"{random.choice(creative_prefixes)} {base_name}"
            else:
                artwork_name = f"{base_name} {random.choice(creative_suffixes)}"
        else:
            artwork_name = base_name

        metadata = {
            "name": artwork_name,
            "artist": random.choice(self.artists),
            "artwork_type": random.choice(self.artwork_types),
            "medium": random.choice(self.mediums),
            "style": random.choice(self.styles),
            "dimensions": random.choice(self.dimensions),
            "year_created": random.randint(1950, 2024),
            "price": round(random.uniform(250, 15000), 2)
        }

        return metadata

    def process_image(self, image_path):
        """Process a single image and add it to the database"""
        try:
            print(f"Processing: {image_path}")

            with open(image_path, "rb") as f:
                image_data = f.read()

            # Validate image
            try:
                img = Image.open(io.BytesIO(image_data))
                img.verify()
            except Exception as e:
                print(f"Invalid image file {image_path}: {e}")
                return False

            filename = os.path.basename(image_path)
            metadata = self.generate_artwork_metadata(filename)

            description = self.generate_description_with_ai(
                metadata["name"],
                metadata["artist"],
                metadata["style"],
                metadata["medium"],
                metadata["artwork_type"]
            )

            print(f"Creating 3D model for {metadata['name']}...")
            glb_bytes = create_glb_from_image(io.BytesIO(image_data))

            if not glb_bytes:
                print(f"Failed to create GLB for {image_path}")
                return False

            artwork = Artwork(
                name=metadata["name"],
                description=description,
                price=metadata["price"],
                artwork_type=metadata["artwork_type"],
                artist=metadata["artist"],
                year_created=metadata["year_created"],
                dimensions=metadata["dimensions"],
                medium=metadata["medium"],
                style=metadata["style"],
                image_data=image_data,
                glb_data=glb_bytes,
                filename=filename
            )

            db.session.add(artwork)
            db.session.commit()

            print(f"✅ Successfully added: {metadata['name']} by {metadata['artist']}")
            return True

        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            db.session.rollback()
            return False

    def populate_from_folder(self, folder_path):
        """Process all images in the specified folder"""
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist!")
            return

        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}

        image_files = []
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(filename.lower())
                if ext in image_extensions:
                    image_files.append(file_path)

        if not image_files:
            print(f"No image files found in {folder_path}")
            return

        print(f"Found {len(image_files)} image files to process")
        print("=" * 50)

        success_count = 0

        # Create Flask app context properly
        app = create_app()
        with app.app_context():
            for image_path in image_files:
                if self.process_image(image_path):
                    success_count += 1

        print("=" * 50)
        print(f"Processing complete! Successfully added {success_count}/{len(image_files)} artworks")


def main():
    print("🎨 AR Gallery Artwork Populator")
    print("=" * 50)

    gemini_api_key = input("Enter your Gemini API key (or press Enter to skip AI descriptions): ").strip()
    if not gemini_api_key:
        print("⚠️  No API key provided. Will use fallback descriptions.")
        gemini_api_key = None

    data_folder = input("Enter the path to your artwork images folder (default: ./data): ").strip()
    if not data_folder:
        data_folder = "./data"

    populator = ArtworkPopulator(gemini_api_key)
    populator.populate_from_folder(data_folder)

    print("\n🎉 Done! Check the buyer page to see your new artworks!")


if __name__ == "__main__":
    main()
