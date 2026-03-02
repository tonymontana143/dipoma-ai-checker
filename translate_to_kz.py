#!/usr/bin/env python3
"""
Перевод русскоязычного датасета в казахский (бесплатно).
Использует googletrans (Google Translate бесплатный API без регистрации).
"""

import os
import pandas as pd
from googletrans import Translator
from tqdm import tqdm
import time

INPUT_CSV = os.getenv("INPUT_CSV", "labeled.csv")
OUTPUT_CSV = os.getenv("OUTPUT_CSV", "labeled_kz.csv")
TEXT_COL = os.getenv("TEXT_COL", "comment")
LABEL_COL = os.getenv("LABEL_COL", "toxic")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))


def translate_texts(texts):
    """Перевод списка текстов через Google Translate"""
    translator = Translator()
    translated = []
    
    for text in tqdm(texts, desc="Перевод RU→KZ (Google Translate)"):
        try:
            result = translator.translate(text, src='ru', dest='kk')
            translated.append(result.text if result else text)
            time.sleep(0.1)  # Чтобы не было блокировки
        except Exception as e:
            print(f"⚠️ Ошибка перевода: {e}, текст: {text[:50]}")
            translated.append(text)  # Оставляем оригинал
    
    return translated


def main():
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"Не найден файл: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)
    if TEXT_COL not in df.columns or LABEL_COL not in df.columns:
        raise ValueError(f"Ожидаются колонки: {TEXT_COL}, {LABEL_COL}")

    texts = df[TEXT_COL].fillna("").astype(str).tolist()
    print(f"📊 Всего текстов для перевода: {len(texts)}")
    
    translated = translate_texts(texts)

    out_df = pd.DataFrame(
        {
            "comment": translated,
            "toxic": df[LABEL_COL].astype(int).values,
            "lang": "kk",
        }
    )
    out_df.to_csv(OUTPUT_CSV, index=False)
    print(f"✓ Перевод завершен: {OUTPUT_CSV} ({len(out_df)} строк)")


if __name__ == "__main__":
    main()
