import os
import re
import shutil
from rapidfuzz import fuzz

# === ПАРСИНГ ===
def extract_heal_info(text):
    for line in text.splitlines():
        if fuzz.partial_ratio("вы вылечили", line.lower()) > 80:
            match = re.search(r"выл[её]чили\D*(\d+)", line, re.IGNORECASE)
            if match:
                return match.group(0), match.group(1)
    return None, None

def extract_datetime(text):
    pattern = r'(\d{1,2})[.:](\d{2})\s+(\d{2})[.\-/]?(\d{2})[.\-/]?(\d{4})'
    match = re.search(pattern, text)
    if match:
        h, m, d, mo, y = match.groups()
        return f"{h.zfill(2)}:{m} {d.zfill(2)}.{mo.zfill(2)}.{y}"
    return None

# === ЛОКАЦИИ ===
LOCATION_MAP = {
    "Эль-Бурро-Хайтс": "ELSH",
    "Сэнди-Шорс": "Sandy-Shores",
    "Палето-Бэй": "Paleto-Bay",
}

def detect_location(text):
    for line in text.splitlines():
        for loc_name, folder_name in LOCATION_MAP.items():
            if fuzz.partial_ratio(loc_name.lower(), line.lower()) > 85:
                return folder_name
    return None

# === ОСНОВНОЙ СКРИПТ ===
def process_files(text_folder, image_folder, output_root):
    for txt_file in os.listdir(text_folder):
        if not txt_file.lower().endswith(".txt"):
            continue

        txt_path = os.path.join(text_folder, txt_file)
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()

        heal_line, heal_id = extract_heal_info(content)
        dt = extract_datetime(content)
        loc_folder = detect_location(content)

        if heal_id and dt and loc_folder:
            # По имени текста ищем изображение
            base_name = os.path.splitext(txt_file)[0]
            image_path = None
            for ext in ['.png', '.jpg', '.jpeg', '.bmp']:
                candidate = os.path.join(image_folder, base_name + ext)
                if os.path.exists(candidate):
                    image_path = candidate
                    break

            if image_path:
                safe_date = dt.replace(":", "-").replace(".", "-")
                new_name = f"Heal - {safe_date}{os.path.splitext(image_path)[1]}"
                output_path = os.path.join(output_root, loc_folder)
                os.makedirs(output_path, exist_ok=True)
                shutil.copy(image_path, os.path.join(output_path, new_name))
                print(f"[✔] Скопировано: {new_name} → {loc_folder}")
            else:
                print(f"[!] Не найдено изображение для {txt_file}")
        else:
            print(f"[ ] Пропущено (нет 'вылечили' или даты или локации): {txt_file}")

# === ПУТИ ===
text_folder = "output_texts"
image_folder = "images"
output_root = "output_images/heal"

process_files(text_folder, image_folder, output_root)
