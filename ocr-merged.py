import logging
import easyocr
import os
from glob import glob
import re
import shutil
import json
from rapidfuzz import fuzz, process

# Configure logging
logging.basicConfig(
    filename='app.log',         # Log file name
    filemode='a',               # Append mode ('w' to overwrite)
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO          # Minimum level to log
)

# OCR PART

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
    logging.info(f"Saved text from {image_path} to {txt_path}")


# Sorting part 



# === ЛОКАЦИИ ИЗ JSON ===
def load_location_map(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {loc['name']: 'City' if loc['City'] == 1 else 'NotCity' for loc in data['locations']}

# === ПАРСИНГ ДЕЙСТВИЯ ===
def detect_action(text):
    for line in text.splitlines():
        l = line.lower()
        if fuzz.partial_ratio("вы вылечили", l) > 80:
            match = re.search(r"выл[её]чили\D+([A-Za-zА-Яа-яЁё0-9_ ]{3,40})", line, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if 1 <= len(name.split()) <= 2:
                    return "heal", name
        elif fuzz.partial_ratio("вы вакцинировали", l) > 80:
            match = re.search(r"вакцинировали\D+([A-Za-zА-Яа-яЁё0-9_ ]{3,40})", line, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if 1 <= len(name.split()) <= 2:
                    return "vaccine", name
        elif fuzz.partial_ratio("вы реанимировали", l) > 80:
            match = re.search(r"реанимировали\D+([A-Za-zА-Яа-яЁё0-9_ ]{3,40})", line, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if 1 <= len(name.split()) <= 2:
                    return "reanimation", name
    return None, None


# === ДАТА + ОПРЕДЕЛЕНИЕ ДНЯ/НОЧИ ===
def extract_datetime(text):
    pattern = r'(\d{1,2})[.:](\d{2})\s+(\d{2})[.\-/]?(\d{2})[.\-/]?(\d{4})'
    match = re.search(pattern, text)
    if match:
        h, m, d, mo, y = match.groups()
        hour = int(h)
        time_of_day = "Day" if 12 <= hour < 22 else "Night"
        full = f"{h.zfill(2)}:{m} {d.zfill(2)}.{mo.zfill(2)}.{y}"
        return full, time_of_day
    return None, None

# === ОБЫЧНЫЕ ЛОКАЦИИ ===
LOCATION_MAP = {
    "Эль-Бурро-Хайтс": "ELSH",
    "Сэнди-Шорс": "Sandy-Shores",
    "Палето-Бэй": "Paleto-Bay",
}

def detect_simple_location(text):
    for line in text.splitlines():
        for loc_name, folder_name in LOCATION_MAP.items():
            if fuzz.partial_ratio(loc_name.lower(), line.lower()) > 85:
                return folder_name
    return None

# === ЛОКАЦИЯ ДЛЯ REANIMATION ===
def detect_reanimation_location(text, reanimation_location_map):
    for line in text.splitlines():
        for loc_name in reanimation_location_map:
            if fuzz.partial_ratio(loc_name.lower(), line.lower()) > 85:
                return loc_name, reanimation_location_map[loc_name]
    return None, None

# === ОСНОВНАЯ ЛОГИКА ===
def process_files(text_folder, image_folder, output_root, location_json_path):
    reanimation_location_map = load_location_map(location_json_path)

    for txt_file in os.listdir(text_folder):
        if not txt_file.lower().endswith(".txt"):
            continue

        txt_path = os.path.join(text_folder, txt_file)
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()

        action_type, person_id = detect_action(content)
        dt_full, time_of_day = extract_datetime(content)

        if not action_type or not dt_full:
            # Place in 'various' if action or date is missing
            base_name = os.path.splitext(txt_file)[0]
            image_path = find_image(base_name, image_folder)
            if image_path:
                various_path = os.path.join(output_root, 'various')
                os.makedirs(various_path, exist_ok=True)
                new_name = f"Various - {base_name}{os.path.splitext(image_path)[1]}"
                try:
                    shutil.copy(image_path, os.path.join(various_path, new_name))
                    print(f"[~] No action/date: {new_name} → {various_path}")
                    logging.info(f"[~] No action/date: {new_name} -> {various_path}")
                except Exception as e:
                    logging.error(f"Failed to copy {image_path} to {various_path}: {e}")
                    print(f"[!] Failed to copy {image_path} to {various_path}: {e}")
            else:
                print(f"[ ] Пропущено (нет действия или даты): {txt_file}")
                logging.warning(f"[ ] Skipped (no action or date): {txt_file}")
            continue

        # === Определяем путь сохранения ===
        output_path = None

        if action_type == "reanimation":
            loc_name, city_flag = detect_reanimation_location(content, reanimation_location_map)
            if not loc_name:
                print(f"[!] Локация не найдена для реанимации: {txt_file}")
                logging.warning(f"[!] Location is not found for reanimation: {txt_file}")

                continue
            output_path = os.path.join(output_root, action_type, city_flag, time_of_day)
        else:
            simple_loc = detect_simple_location(content)
            if not simple_loc:
                print(f"[!] Локация не найдена для {action_type}: {txt_file}")
                logging.warning(f"[!] Location is not found for {action_type}: {txt_file}")
                continue
            output_path = os.path.join(output_root, action_type, simple_loc)

        # === Ищем изображение ===
        base_name = os.path.splitext(txt_file)[0]
        image_path = None
        for ext in ['.png', '.jpg', '.jpeg', '.bmp']:
            candidate = os.path.join(image_folder, base_name + ext)
            if os.path.exists(candidate):
                image_path = candidate
                break

        if not image_path:
            print(f"[!] Изображение не найдено: {txt_file}")
            logging.warning(f"[!] Image is not found: {txt_file}")

            continue

        # === Сохраняем ===
        os.makedirs(output_path, exist_ok=True)
        safe_date = dt_full.replace(":", "-").replace(".", "-")
        new_name = f"{action_type.capitalize()} - {safe_date}{os.path.splitext(image_path)[1]}"
        shutil.copy(image_path, os.path.join(output_path, new_name))
        print(f"[✔] {action_type.capitalize()} → {new_name} → {output_path}")
        logging.info(f"[+] {action_type.capitalize()} -> {new_name} -> {output_path}")


# === ПУТИ ===
text_folder = "output_texts"
image_folder = "images"
output_root = "output_images"
location_json_path = "gta-locations.json"

process_files(text_folder, image_folder, output_root, location_json_path)
