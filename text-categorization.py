import os
import re
import shutil
from rapidfuzz import fuzz

# === ЛОКАЦИИ ===
LOCATION_MAP = {
    "Эль-Бурро-Хайтс": "ELSH",
    "Сэнди-Шорс": "Sandy-Shores",
    "Палето-Бэй": "Paleto-Bay",
}

# === ОБРАБОТКА ТЕКСТА ===

def detect_action(text):
    """
    Ищет действие: 'вылечили' или 'вакцинировали'.
    Возвращает ('heal' или 'vaccine', id) или (None, None)
    """
    for line in text.splitlines():
        l = line.lower()
        if fuzz.partial_ratio("вы вылечили", l) > 80:
            match = re.search(r"выл[её]чили\D*(\d+)", line, re.IGNORECASE)
            if match:
                return "heal", match.group(1)
        elif fuzz.partial_ratio("вы вакцинировали", l) > 80:
            match = re.search(r"вакцинировали\D*(\d+)", line, re.IGNORECASE)
            if match:
                return "vaccine", match.group(1)
    return None, None

def extract_datetime(text):
    pattern = r'(\d{1,2})[.:](\d{2})\s+(\d{2})[.\-/]?(\d{2})[.\-/]?(\d{4})'
    match = re.search(pattern, text)
    if match:
        h, m, d, mo, y = match.groups()
        return f"{h.zfill(2)}:{m} {d.zfill(2)}.{mo.zfill(2)}.{y}"
    return None

def detect_location(text):
    for line in text.splitlines():
        for loc_name, folder_name in LOCATION_MAP.items():
            if fuzz.partial_ratio(loc_name.lower(), line.lower()) > 85:
                return folder_name
    return None

# === ОСНОВНАЯ ЛОГИКА ===

def process_files(text_folder, image_folder, output_root):
    for txt_file in os.listdir(text_folder):
        if not txt_file.lower().endswith(".txt"):
            continue

        txt_path = os.path.join(text_folder, txt_file)
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()

        action_type, person_id = detect_action(content)
        dt = extract_datetime(content)
        loc_folder = detect_location(content)

        if action_type and dt and loc_folder:
            base_name = os.path.splitext(txt_file)[0]
            image_path = None
            for ext in ['.png', '.jpg', '.jpeg', '.bmp']:
                candidate = os.path.join(image_folder, base_name + ext)
                if os.path.exists(candidate):
                    image_path = candidate
                    break

            if image_path:
                safe_date = dt.replace(":", "-").replace(".", "-")
                new_name = f"{action_type.capitalize()} - {safe_date}{os.path.splitext(image_path)[1]}"
                final_output = os.path.join(output_root, action_type, loc_folder)
                os.makedirs(final_output, exist_ok=True)
                shutil.copy(image_path, os.path.join(final_output, new_name))
                print(f"[✔] {action_type.capitalize()} сохранён: {new_name} → {loc_folder}")
            else:
                print(f"[!] Не найдено изображение для {txt_file}")
        else:
            print(f"[ ] Пропущено: {txt_file} (нет действия, даты или локации)")

# === ПУТИ ===
text_folder = "output_texts"
image_folder = "images"
output_root = "output_images"

process_files(text_folder, image_folder, output_root)
