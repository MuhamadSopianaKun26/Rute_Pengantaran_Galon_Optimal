"""
history_logic.py
Penyimpanan riwayat customer (dibatalkan & selesai) pada JSON.

Fungsi:
- get_history_data_path()
- load_history()
- save_history(records)
- ensure_dummy_history()
"""

import json
import os
from typing import List, Dict


def get_history_data_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, "Database", "customer_history.json")


def load_history() -> List[Dict]:
    path = get_history_data_path()
    try:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = f.read().strip()
            if not data:
                return []
            return json.loads(data)
    except Exception:
        return []


def save_history(records: List[Dict]) -> bool:
    path = get_history_data_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def ensure_dummy_history() -> None:
    existing = load_history()
    if existing:
        return
    demo = [
        {
            "id": "HIST-1001",
            "source_order": "ORD-010",
            "customer_name": "Sinta",
            "items": ["Galon Aqua 19L"],
            "finished_at": "2025-10-10 09:20",
            "status": "selesai"
        },
        {
            "id": "HIST-1002",
            "source_order": "ORD-011",
            "customer_name": "Rudi",
            "items": ["Galon Aqua 19L", "Tutup Galon"],
            "canceled_at": "2025-10-11 12:05",
            "status": "dibatalkan",
            "note": "Dibatalkan oleh penjual"
        }
    ]
    save_history(demo)


ensure_dummy_history()
