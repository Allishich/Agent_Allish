#!/usr/bin/env python3
"""Восстановление полного CSV ВПН-2020 из 8 CSV-частей в research_data/.
Никаких сетевых запросов. Исходные файлы GitHub не изменяются.
Запуск из корня репозитория: python research_data/tools/reconstruct_large_csv.py
"""
from pathlib import Path
import hashlib
import csv
import io
import sys

PACKAGE = Path(__file__).resolve().parents[1]
NAME = "ru_vpn2020_tab04_households_children_structure_by_region"
PARTS = PACKAGE / "datasets" / "demography" / "parts"
OUTPUT = PACKAGE / "datasets" / "demography" / (NAME + ".csv")
SHA256_EXPECTED = "b12866833a7a9b4f31f44c6490ad87012226d8b856fc871ce5dead628f4d663a"
SIZE_EXPECTED = 4535353
ROWS_EXPECTED = 9120

def main() -> int:
    paths = [PARTS / f"{NAME}.part_{i:02d}.csv" for i in range(1, 9)]
    if any(not p.is_file() for p in paths):
        print("Отсутствуют части:", [str(p) for p in paths if not p.is_file()], file=sys.stderr)
        return 1

    first = paths[0].read_bytes()
    if b"\n" not in first:
        print("Не обнаружен заголовок CSV", file=sys.stderr)
        return 1
    header = first.split(b"\n", 1)[0] + b"\n"
    content = bytearray(first)
    for part in paths[1:]:
        blob = part.read_bytes()
        if not blob.startswith(header):
            print("Несовпадающий заголовок:", part.name, file=sys.stderr)
            return 1
        content.extend(blob[len(header):])

    data = bytes(content)
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != SIZE_EXPECTED or digest != SHA256_EXPECTED:
        print(f"Контрольная сумма или размер не совпали: {len(data)} байт; {digest}", file=sys.stderr)
        return 1

    with io.StringIO(data.decode("utf-8-sig"), newline="") as stream:
        rows = sum(1 for _ in csv.reader(stream)) - 1
    if rows != ROWS_EXPECTED:
        print(f"Ожидалось {ROWS_EXPECTED} строк; получено {rows}", file=sys.stderr)
        return 1

    if OUTPUT.exists():
        if OUTPUT.read_bytes() == data:
            print("Полный CSV уже существует и проверен:", OUTPUT)
            return 0
        print("Целевой файл существует и отличается; ничего не перезаписано:", OUTPUT, file=sys.stderr)
        return 1
    OUTPUT.write_bytes(data)
    print(f"Восстановлено: {OUTPUT} | {len(data)} байт | {rows} строк | sha256={digest}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
