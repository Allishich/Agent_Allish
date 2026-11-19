#!/usr/bin/env python3
"""Валидация автономного пакета research_data/ без сетевых запросов."""
from pathlib import Path
import csv
import hashlib
import io
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
NAV = ROOT / "AI_CONTEXT"
ERRORS = []
WARNINGS = []

def read(name):
    return json.loads((NAV / name).read_text(encoding="utf-8-sig"))

def safe(path):
    if not isinstance(path, str) or not path.startswith("research_data/"):
        ERRORS.append(f"Некорректный локальный путь: {path!r}")
        return None
    rel = Path(path).relative_to("research_data")
    if ".." in rel.parts:
        ERRORS.append(f"Недопустимый путь: {path}")
        return None
    dest = ROOT / rel
    if not dest.is_file():
        ERRORS.append(f"Файл не найден: {path}")
        return None
    return dest

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    m = read("manifest.json")
    r = read("routing.json")
    i = read("inventory.json")
    d = m.get("indexed_datasets", [])
    if len(d) != 43:
        ERRORS.append(f"Ожидалось 43 набора, найдено {len(d)}")
    ids = set()
    data_ok = 0
    passports_ok = 0
    for entry in d:
        id_ = entry["dataset_id"]
        if id_ in ids:
            ERRORS.append(f"Повтор dataset_id {id_}")
        ids.add(id_)
        f = entry["data_file"]
        if f.get("repository_path"):
            p = safe(f["repository_path"])
            if p is not None:
                data = p.read_bytes()
                data_ok += 1
        else:
            parts = f.get("repository_parts") or []
            if len(parts) != 8 or entry.get("native_dataset_id") != "RU-VPN2020-TAB04":
                ERRORS.append(f"Нет полноценного пути или описанных частей для {id_}")
                continue
            fragments = [safe(x) for x in parts]
            if any(x is None for x in fragments):
                continue
            blob = fragments[0].read_bytes()
            header = blob.split(b"\n", 1)[0] + b"\n"
            if not blob.startswith(header):
                ERRORS.append("Нет заголовка в первом фрагменте ВПН")
                continue
            for part in fragments[1:]:
                content = part.read_bytes()
                if not content.startswith(header):
                    ERRORS.append(f"Несовпадающий заголовок {part}")
                    break
                blob += content[len(header):]
            else:
                if sha(blob) != f["original_sha256"]:
                    ERRORS.append("Сбой SHA256 восстановленного ВПН-2020")
                elif len(blob) != 4535353:
                    ERRORS.append("Сбой размера восстановленного ВПН-2020")
                else:
                    data_ok += 1
            data = blob
        meta = entry.get("metadata_file")
        if meta:
            mp = safe(meta.get("repository_path"))
            if mp:
                obj = json.loads(mp.read_text(encoding="utf-8-sig"))
                passports_ok += 1
                expected = obj.get("sha256_csv") or obj.get("sha256")
                if expected and f.get("repository_path") and sha(data) != expected:
                    ERRORS.append(f"SHA256 не совпадает: {id_}")
        catalog = entry.get("source_catalog")
        if catalog and catalog.get("repository_path"):
            safe(catalog["repository_path"])

    if len(i["files"]) != i.get("file_count"):
        ERRORS.append("Неверное количество записей исходного инвентаря")
    paths = [x["file_id"] for x in i["files"]]
    if len(paths) != len(set(paths)):
        ERRORS.append("Повторяющиеся file_id в инвентаре")
    for route in r["routes"]:
        candidate_ids = route.get("candidate_dataset_ids", [])
        references = route.get("candidate_repository_files", [])
        if len(candidate_ids) != len(references):
            ERRORS.append("Несовпадение ссылок маршрута " + route["intent_id"])
        for ref in references:
            if ref["dataset_id"] not in ids:
                ERRORS.append("Неизвестный dataset_id маршрута " + ref["dataset_id"])
    for name in ["data_rules.md", "DATASETS_OVERVIEW.md", "examples.md",
                 "inventory_report.json", "INSTRUCTION_FOR_COLLEAGUE_GPT.yaml"]:
        if not (NAV / name).is_file():
            ERRORS.append("Нет навигационного документа " + name)
    result = {"passed": not ERRORS, "datasets": len(d),
              "csv_datasets_verified": data_ok,
              "individual_passports_found": passports_ok,
              "routes": len(r["routes"]), "errors": ERRORS, "warnings": WARNINGS}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not ERRORS else 1

if __name__ == "__main__":
    sys.exit(main())
