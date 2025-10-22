"""
UI_cs_order.py
Dialog Pemesanan (PyQt6) yang muncul ketika bottom bar "Pesan" ditekan.

Fitur:
- Form: Atas Nama, Area, Jalan (dependent), Keterangan
- Waktu pengiriman: dropdown mode (Segera/Terjadwal) + waktu (aktif jika Terjadwal)
- Item: dropdown produk + harga, spin jumlah, tombol Tambah -> list item di bawah (scroll kecil)
- Total harga barang + placeholder total biaya pengiriman
- Tombol Batal dan Pesan (Pesan aktif setelah valid)
- Simpan ke Database/order_data.json via logic.file.order_logic
"""

from PyQt6.QtCore import Qt
import os, json, datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QWidget, QScrollArea, QFrame, QMessageBox, QListWidget, QListWidgetItem, QSpinBox, QListView
)

try:
    from logic.file.order_logic import load_orders, save_orders
except Exception:
    def load_orders():
        return []
    def save_orders(_):
        return False


AREA_TO_STREETS = {
    "Ciwaruga": ["Jl. Ciwaruga 1", "Jl. Ciwaruga 2"],
    "Sarijadi raya": ["Jl. Sarijadi Raya 1", "Jl. Sarijadi Raya 2"],
    "Gerlong hilir": ["Jl. Gerlong Hilir 1", "Jl. Gerlong Hilir 2"],
    "sarimanah": ["Jl. Sarimanah 1", "Jl. Sarimanah 2"],
    "sari asih": ["Jl. Sari Asih 1", "Jl. Sari Asih 2"],
    "sari rasa": ["Jl. Sari Rasa 1", "Jl. Sari Rasa 2"],
}

PRODUCTS = {
    "Galon Aqua 19L": 20000,
    "Tutup Galon": 2000,
    "Air Mineral 600ml (6 pcs)": 25000,
}

def _db_path(filename: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, 'Database', filename)

def _graph_path(filename: str) -> str:
    """Bangun path file graph (geojson, cache) di folder logic/graph/"""
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, 'logic', 'graph', filename)

def _load_products_from_json() -> dict:
    path = _db_path('products.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = data.get('products', [])
        return {it.get('name', ''): int(it.get('price', 0)) for it in items if it.get('name')}
    except Exception:
        return PRODUCTS

def _load_areas_from_json() -> dict:
    path = _db_path('areas.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        areas = {}
        for a in data.get('areas', []):
            name = a.get('name') or ''
            streets = a.get('streets') or []
            if name:
                areas[name] = list(streets)
        return areas or AREA_TO_STREETS
    except Exception:
        return AREA_TO_STREETS

def _load_area_streets_from_geojson() -> dict:
    """Muat mapping region -> [intersection_name] dari file GeoJSON.
    Fallback ke data JSON lama atau konstanta jika gagal."""
    path = _graph_path('intersections_area.geojson')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        area_map: dict[str, set] = {}
        for feat in data.get('features', []):
            props = (feat or {}).get('properties') or {}
            region = props.get('region_name') or ''
            inter = props.get('intersection_name') or ''
            if region and inter:
                area_map.setdefault(region, set()).add(inter)
        # Konversi set ke list terurut untuk stabilitas UI
        if area_map:
            return {k: sorted(v) for k, v in area_map.items()}
        # Jika kosong, fallback ke JSON lama atau konstanta
        return _load_areas_from_json() or AREA_TO_STREETS
    except Exception:
        # Fallback bertahap agar UI tetap berfungsi
        try:
            return _load_areas_from_json() or AREA_TO_STREETS
        except Exception:
            return AREA_TO_STREETS

SCHEDULE_TIMES = ["09.00", "12.00", "15.00", "18.00"]


class OrderDialog(QDialog):
    """Dialog pemesanan berukuran 800x600, modal, dengan validasi dan penyimpanan."""

    def __init__(self, parent=None, current_user: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Pemesanan")
        self.resize(800, 600)
        self.setModal(True)
        self.current_user = current_user or {}
        # Style mirip right_panel login: putih semi-transparan
        self.setStyleSheet(
            """
            QDialog {
                background-color: rgba(255, 255, 255, 0.95);
            }
            QLineEdit, QComboBox, QListWidget {
                font-size: 14px;
            }
            """
        )

        self.items = []  # list of dict: {name, price, qty}

        self._build_ui()
        self._wire_events()
        self._refresh_totals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # 1. Label Pemesanan
        title = QLabel("Pemesanan")
        title.setObjectName("OrderTitle")
        title.setStyleSheet("QLabel#OrderTitle { font-size: 20px; font-weight: 800; color: #0f5b6b; }")
        layout.addWidget(title)

        # 2. Atas Nama
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Atas Nama")
        layout.addWidget(self.input_name)

        # 3. Area, Jalan (dependent), Keterangan
        area_row = QHBoxLayout()
        self.combo_area = QComboBox()
        self.combo_area.addItem("-- Pilih Daerah --")
        self._area_map = _load_area_streets_from_geojson()
        for a in sorted(self._area_map.keys()):
            self.combo_area.addItem(a)
        self.combo_street = QComboBox()
        self.combo_street.addItem("-- Pilih Jalan --")
        self.input_note = QLineEdit()
        self.input_note.setPlaceholderText("nomor rumah, warna rumah, dll...")
        area_row.addWidget(self.combo_area)
        area_row.addWidget(self.combo_street)
        area_row.addWidget(self.input_note)
        row_area_widget = QWidget()
        row_area_widget.setLayout(area_row)
        layout.addWidget(row_area_widget)

        # 4. Waktu pengiriman (mode + waktu terjadwal)
        time_row = QHBoxLayout()
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["-- Pilih Mode --", "Pengiriman Segera", "Pengiriman Terjadwal"])
        self.combo_time = QComboBox()
        self.combo_time.addItem("-- Pilih Waktu --")
        self.combo_time.addItems(SCHEDULE_TIMES)
        self.combo_time.setEnabled(False)
        time_row.addWidget(self.combo_mode)
        time_row.addWidget(self.combo_time)
        time_row_widget = QWidget()
        time_row_widget.setLayout(time_row)
        layout.addWidget(time_row_widget)

        # 5. Produk + jumlah + tombol tambah, lalu list item (scroll kecil)
        product_row = QHBoxLayout()
        self.combo_product = QComboBox()
        # Lebarkan dropdown agar harga tidak terpotong
        self.combo_product.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        lv = QListView()
        lv.setMinimumWidth(420)
        self.combo_product.setView(lv)
        self._products = _load_products_from_json()
        for name, price in self._products.items():
            self.combo_product.addItem(f"{name}\tRp{price:,}", userData={"name": name, "price": price})
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 100)
        self.btn_add_item = QPushButton("Tambah")
        self.btn_add_item.setStyleSheet("background:#2ecc71;color:white;font-weight:700;padding:6px 12px;border-radius:8px;")
        self.btn_remove_item = QPushButton("Hapus Item")
        self.btn_remove_item.setStyleSheet("background:#e74c3c;color:white;font-weight:700;padding:6px 12px;border-radius:8px;")
        product_row.addWidget(self.combo_product)
        product_row.addWidget(self.spin_qty)
        product_row.addWidget(self.btn_add_item)
        product_row.addWidget(self.btn_remove_item)
        product_row_widget = QWidget()
        product_row_widget.setLayout(product_row)
        layout.addWidget(product_row_widget)

        # Kontainer dengan background untuk list pesanan + total
        self.list_items = QListWidget()
        self.list_items.setFixedHeight(140)

        totals_box = QVBoxLayout()
        self.label_total_barang = QLabel("")
        self.label_total_ongkir = QLabel("")
        totals_box.addWidget(self.label_total_barang)
        totals_box.addWidget(self.label_total_ongkir)
        totals_widget = QWidget()
        totals_widget.setLayout(totals_box)

        items_panel = QFrame()
        items_panel.setObjectName("ItemsPanel")
        items_panel_layout = QVBoxLayout(items_panel)
        items_panel_layout.setContentsMargins(12, 12, 12, 12)
        items_panel_layout.setSpacing(8)
        items_panel_layout.addWidget(self.list_items)
        items_panel_layout.addWidget(totals_widget)
        items_panel.setStyleSheet(
            """
            QFrame#ItemsPanel {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 12px;
            }
            """
        )
        layout.addWidget(items_panel)

        # 7. Tombol Batal dan Pesan
        btn_row = QHBoxLayout()
        self.btn_cancel = QPushButton("Batal")
        self.btn_submit = QPushButton("Pesan")
        self.btn_submit.setEnabled(False)
        self.btn_submit.setStyleSheet("background:#2196F3;color:white;font-weight:700;padding:8px 16px;border-radius:8px;")
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_submit)
        btn_row_widget = QWidget()
        btn_row_widget.setLayout(btn_row)
        layout.addWidget(btn_row_widget)

    def _wire_events(self):
        self.combo_area.currentIndexChanged.connect(self._on_area_changed)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        self.btn_add_item.clicked.connect(self._on_add_item)
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_submit.clicked.connect(self._on_submit)
        # Validasi input untuk enable tombol Pesan
        self.input_name.textChanged.connect(self._update_submit_enabled)
        self.combo_area.currentIndexChanged.connect(self._update_submit_enabled)
        self.combo_street.currentIndexChanged.connect(self._update_submit_enabled)
        self.combo_mode.currentIndexChanged.connect(self._update_submit_enabled)
        self.combo_time.currentIndexChanged.connect(self._update_submit_enabled)
        # Hapus item yang dipilih
        self.btn_remove_item.clicked.connect(self._on_remove_item)

    def _on_area_changed(self):
        self.combo_street.clear()
        self.combo_street.addItem("-- Pilih Jalan --")
        area = self.combo_area.currentText()
        streets = self._area_map.get(area, [])
        for s in streets:
            self.combo_street.addItem(s)

    def _on_mode_changed(self):
        mode = self.combo_mode.currentText()
        if mode == "Pengiriman Terjadwal":
            self.combo_time.setEnabled(True)
        else:
            self.combo_time.setEnabled(False)
            self.combo_time.setCurrentIndex(0)
        self._update_submit_enabled()

    def _on_add_item(self):
        data = self.combo_product.currentData()
        if not data:
            return
        qty = self.spin_qty.value()
        name = data["name"]
        price = data["price"]
        self.items.append({"name": name, "price": price, "qty": qty})
        item_text = f"{name} x{qty} - Rp{price*qty:,}"
        self.list_items.addItem(QListWidgetItem(item_text))
        self._refresh_totals()
        self._update_submit_enabled()

    def _on_remove_item(self):
        """Hapus item yang dipilih dari daftar dan state items."""
        row = self.list_items.currentRow()
        if row < 0 or row >= len(self.items):
            QMessageBox.information(self, "Tidak ada item", "Pilih item pada daftar untuk dihapus.")
            return
        # Hapus dari state dan UI
        self.items.pop(row)
        itm = self.list_items.takeItem(row)
        del itm
        self._refresh_totals()
        self._update_submit_enabled()

    def _refresh_totals(self):
        subtotal = sum(it["price"] * it["qty"] for it in self.items)
        shipping = "{total biaya pengiriman}"  # placeholder (akan dihitung via Dijkstra)
        self.label_total_barang.setText(f"Total Barang: Rp{subtotal:,}")
        self.label_total_ongkir.setText(f"Total Biaya Pengiriman: {shipping}")

    def _all_inputs_valid(self) -> bool:
        if not self.input_name.text().strip():
            return False
        if self.combo_area.currentIndex() <= 0:
            return False
        if self.combo_street.currentIndex() <= 0:
            return False
        if not self.items:
            return False
        mode = self.combo_mode.currentText()
        if mode == "-- Pilih Mode --":
            return False
        if mode == "Pengiriman Terjadwal" and self.combo_time.currentIndex() <= 0:
            return False
        return True

    def _update_submit_enabled(self):
        self.btn_submit.setEnabled(self._all_inputs_valid())

    def _warn(self, title: str, text: str) -> bool:
        res = QMessageBox.warning(self, title, text, QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        return res == QMessageBox.StandardButton.Ok

    def _on_cancel(self):
        if self._warn("Batalkan Pemesanan", "Apakah Anda yakin ingin membatalkan? Data yang sudah diisi akan hilang." ):
            self.reject()

    def _on_submit(self):
        if not self._all_inputs_valid():
            QMessageBox.warning(self, "Input belum lengkap", "Mohon lengkapi semua input sebelum memesan.")
            return
        if not self._warn("Konfirmasi Pesanan", "Kirim pesanan sekarang?"):
            return
        # Bangun record order
        mode = self.combo_mode.currentText()
        schedule = self.combo_time.currentText() if mode == "Pengiriman Terjadwal" else "Segera"
        order = {
            "id": self._generate_order_id(),
            "customer_name": self.input_name.text().strip(),
            "items": [{"name": it["name"], "qty": it["qty"]} for it in self.items],
            "eta": schedule if schedule != "Segera" else "-",
            "schedule": schedule,
            "status": "menunggu",
            "area": self.combo_area.currentText(),
            "street": self.combo_street.currentText(),
            "note": self.input_note.text().strip(),
            "created_at": datetime.datetime.now().isoformat(),
            # Info user untuk filtrasi per pengguna
            "user_name": self.current_user.get("name"),
            "user_email": self.current_user.get("email"),
        }
        orders = load_orders() or []
        orders.append(order)
        if save_orders(orders):
            QMessageBox.information(self, "Berhasil", "Pesanan berhasil disimpan.")
            self.accept()
        else:
            QMessageBox.critical(self, "Gagal", "Gagal menyimpan pesanan.")

    def _generate_order_id(self) -> str:
        # Sederhana: cari ORD-xxx terbesar dan tambah 1
        orders = load_orders() or []
        max_n = 0
        for o in orders:
            oid = o.get("id", "")
            if isinstance(oid, str) and oid.startswith("ORD-"):
                try:
                    n = int(oid.split("-")[-1])
                    if n > max_n:
                        max_n = n
                except Exception:
                    pass
        return f"ORD-{max_n+1:03d}"

