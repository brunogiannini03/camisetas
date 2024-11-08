from PIL import Image
import sys

if len(sys.argv) != 2:
    print("Usage: python script.py overlay_image.jpg")
    sys.exit(1)

overlay_filename = sys.argv[1]

# Open the base and overlay images
base_image = Image.open('camisetabasica.jpg')
overlay_image = Image.open(overlay_filename)

# Get dimensions
base_width, base_height = base_image.size
overlay_width, overlay_height = overlay_image.size

# Calculate position to center the overlay
position = (
    (base_width - overlay_width) // 2,
    (base_height - overlay_height) // 2
)

# Paste the overlay image onto the base image
base_image.paste(overlay_image, position, overlay_image.convert("RGBA"))

# Save the result
base_image.save('result.jpg')
