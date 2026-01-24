# giveaway_data.py
import json
import os

GIVEAWAY_DATA_FILE = "giveaways.json"


def load_giveaway_data() -> dict:
    if os.path.exists(GIVEAWAY_DATA_FILE):
        try:
            with open(GIVEAWAY_DATA_FILE, "r", encoding="utf-8") as f:
                file_content = json.load(f)
                return file_content.get("current_giveaway", {})
        except (json.JSONDecodeError, KeyError):
            print("[РОЗЫГРЫШ] Ошибка чтения giveaways.json — файл повреждён или пустой. Начинаем с чистого листа.")
            return {}
    return {}


def save_giveaway_data(data: dict) -> None:
    save_content = {"current_giveaway": data}
    try:
        with open(GIVEAWAY_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(save_content, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[РОЗЫГРЫШ] Ошибка сохранения giveaways.json: {e}")