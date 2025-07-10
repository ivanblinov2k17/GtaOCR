import easyocr
import os
from glob import glob

# Create the reader once
reader = easyocr.Reader(['en', 'ru'])

# Directory with images
input_dir = 'images'  # change this if needed
output_dir = 'output_texts'
os.makedirs(output_dir, exist_ok=True)

# Get all PNG and JPG files (adjust pattern if needed)
image_paths = glob(os.path.join(input_dir, '*.png')) + glob(os.path.join(input_dir, '*.jpg'))

# Process each image
for image_path in image_paths:
    results = reader.readtext(image_path)
    
    # Extract just the text
    lines = [text for _, text, _ in results]

    # Prepare output path
    image_name = os.path.splitext(os.path.basename(image_path))[0]
    txt_path = os.path.join(output_dir, f"{image_name}.txt")

    # Save to file
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"Saved text from {image_path} to {txt_path}")