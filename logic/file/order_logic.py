"""
order_logic.py
Logika penyimpanan dan pemuatan data pesanan (JSON) untuk halaman Customer.

Fungsi utama:
- get_order_data_path(): path file JSON
- load_orders(): baca data pesanan dari JSON
- save_orders(orders): simpan list pesanan ke JSON
- ensure_dummy_data(): seed dummy data jika file kosong/tidak ada
"""

import json
import os
from typing import List, Dict


def get_order_data_path() -> str:
    """Kembalikan path absolut ke file JSON order_data.json."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # base_dir menunjuk ke root proyek (perkiraan berdasarkan struktur: logic/file/order_logic.py)
    return os.path.join(base_dir, "Database", "order_data.json")


def load_orders() -> List[Dict]:
    """Membaca list pesanan dari file JSON. Jika tidak ada, kembalikan list kosong."""
    path = get_order_data_path()
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


def save_orders(orders: List[Dict]) -> bool:
    """Menyimpan list pesanan ke file JSON. Mengembalikan True jika berhasil."""
    path = get_order_data_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
