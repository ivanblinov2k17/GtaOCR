import logging
import easyocr
import os
from glob import glob
import re
import shutil
import json
from rapidfuzz import fuzz, process
import argparse
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    filename='app.log',         # Log file name
    filemode='a',               # Append mode ('w' to overwrite)
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO          # Minimum level to log
)

# === HELPERS ===
def find_image(base_name: str, image_folder: str) -> Optional[str]:
    for ext in ['.png', '.jpg', '.jpeg', '.bmp']:
        candidate = os.path.join(image_folder, base_name + ext)
        if os.path.exists(candidate):
            return candidate
    return None

def safe_filename(s: str) -> str:
    return s.replace(":", "-").replace(".", "-")

# === ЛОКАЦИИ ИЗ PY ===
def load_location_map(py_path):
    import importlib.util
    import sys
    import os
    try:
        module_name = os.path.splitext(os.path.basename(py_path))[0]
        spec = importlib.util.spec_from_file_location(module_name, py_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        locations = getattr(module, 'locations', [])
        return {loc['name']: 'City' if loc.get('City') == 1 else 'NotCity' for loc in locations}
    except Exception as e:
        logging.error(f"Failed to load location map from py: {e}")
        return {}

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

# === OCR PART ===
def ocr_images(input_dir: str, output_dir: str, force: bool = False):
    os.makedirs(output_dir, exist_ok=True)
    image_paths = glob(os.path.join(input_dir, '*.png')) + glob(os.path.join(input_dir, '*.jpg'))
    reader = easyocr.Reader(['en', 'ru'])
    for image_path in image_paths:
        image_name = os.path.splitext(os.path.basename(image_path))[0]
        txt_path = os.path.join(output_dir, f"{image_name}.txt")
        if not force and os.path.exists(txt_path):
            logging.info(f"Skipping already processed: {image_path}")
            continue
        try:
            results = reader.readtext(image_path)
            lines = [text for _, text, _ in results]
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print(f"Saved text from {image_path} to {txt_path}")
            logging.info(f"Saved text from {image_path} to {txt_path}")
        except Exception as e:
            logging.error(f"OCR failed for {image_path}: {e}")
            print(f"[!] OCR failed for {image_path}: {e}")

# === MAIN SORTING LOGIC ===
def process_files(text_folder, image_folder, output_root, location_py_path):
    reanimation_location_map = load_location_map(location_py_path)
    for txt_file in os.listdir(text_folder):
        if not txt_file.lower().endswith(".txt"):
            continue
        txt_path = os.path.join(text_folder, txt_file)
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logging.error(f"Failed to read {txt_path}: {e}")
            continue
        action_type, person_id = detect_action(content)
        dt_full, time_of_day = extract_datetime(content)
        if not action_type or not dt_full:
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
        image_path = find_image(base_name, image_folder)
        if not image_path:
            print(f"[!] Изображение не найдено: {txt_file}")
            logging.warning(f"[!] Image is not found: {txt_file}")
            continue
        # === Сохраняем ===
        os.makedirs(output_path, exist_ok=True)
        safe_date = safe_filename(dt_full)
        new_name = f"{action_type.capitalize()} - {safe_date}"
        if person_id:
            new_name += f" - {person_id}"
        new_name += os.path.splitext(image_path)[1]
        try:
            shutil.copy(image_path, os.path.join(output_path, new_name))
            print(f"[✔] {action_type.capitalize()} → {new_name} → {output_path}")
            logging.info(f"[+] {action_type.capitalize()} -> {new_name} -> {output_path}")
        except Exception as e:
            logging.error(f"Failed to copy {image_path} to {output_path}: {e}")
            print(f"[!] Failed to copy {image_path} to {output_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="OCR and sort GTA screenshots.")
    parser.add_argument('--input-dir', default='images', help='Input images directory')
    parser.add_argument('--output-texts', default='output_texts', help='Output texts directory')
    parser.add_argument('--output-images', default='output_images', help='Output images directory')
    parser.add_argument('--location-py', default='gta-locations.py', help='Location path')
    parser.add_argument('--force-ocr', action='store_true', help='Force OCR even if text files exist')
    args = parser.parse_args()

    ocr_images(args.input_dir, args.output_texts, force=args.force_ocr)
    process_files(args.output_texts, args.input_dir, args.output_images, args.location_py)

if __name__ == "__main__":
    main()
