#!/usr/bin/env python3
"""Совместимый вход для ранее использовавшегося validate_index.py.
Проверяет пакет GitHub, а не только ссылки на Google Drive.
"""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1] / "tools" / "validate_package.py"), run_name="__main__")
