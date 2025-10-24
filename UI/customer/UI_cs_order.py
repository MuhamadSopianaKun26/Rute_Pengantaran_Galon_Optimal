"""
UI_cs_order.py
Dialog Pemesanan (PyQt6) yang muncul ketika bottom bar "Pesan" ditekan.
Menggunakan data dinamis dari output.geojson untuk area dan jalan.
"""

from PyQt6.QtCore import Qt
import os
import json
import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QWidget, QScrollArea, QFrame, QMessageBox, QListWidget, QListWidgetItem, QSpinBox, QListView
)

try:
    # Asumsi order_logic.py ada di logic/file/
    from logic.file.order_logic import load_orders, save_orders
except ImportError as e:
    print(f"WARNING: Gagal impor order_logic: {e}. Fungsi simpan/load mungkin tidak bekerja.")
    def load_orders(): return []
    def save_orders(_): return False

# Konstanta PRODUCTS sebagai fallback
DEFAULT_PRODUCTS = {
    "Galon Aqua 19L": 20000,
    "Tutup Galon": 2000,
    "Air Mineral 600ml (6 pcs)": 25000,
}

# --- Helper Functions for Paths ---

def _db_path(filename: str) -> str:
    """Bangun path file di folder Database/"""
    # Asumsi file ini ada di PROYEK/UI/customer/
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, 'Database', filename)

def _graph_path(filename: str) -> str:
    """Bangun path file di folder logic/graph/"""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, 'logic', 'graph', filename)

# --- Helper Functions for Loading Data ---

def _load_products_from_json() -> dict:
    """Muat data produk dari products.json."""
    path = _db_path('products.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = data.get('products', [])
        # Pastikan harga adalah integer
        return {str(it.get('name', '')): int(it.get('price', 0)) for it in items if it.get('name')}
    except FileNotFoundError:
        print(f"File produk tidak ditemukan di {path}. Menggunakan fallback.")
        return DEFAULT_PRODUCTS
    except Exception as e:
        print(f"Error memuat produk dari JSON: {e}. Menggunakan fallback.")
        return DEFAULT_PRODUCTS

# --- [FUNGSI BARU] Memuat Area dan Jalan dari GeoJSON ---
def _load_area_streets_from_geojson() -> dict:
    """
    Muat mapping region -> [intersection_name] dari file output.geojson.
    Fallback ke konstanta jika gagal.
    """
    path = _graph_path('output.geojson')
    area_map: dict[str, set] = {} # Gunakan set untuk otomatis handle duplikat

    try:
        print(f"Mencoba memuat area/jalan dari: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for feat in data.get('features', []):
            props = (feat or {}).get('properties') or {}
            region = props.get('region_name')
            inter = props.get('intersection_name') # Nama persimpangan/jalan

            # Hanya proses jika region dan intersection_name valid (string non-kosong)
            if isinstance(region, str) and region.strip() and \
               isinstance(inter, str) and inter.strip():
                area_map.setdefault(region.strip(), set()).add(inter.strip())

        if not area_map:
            print(f"Tidak ada data region/jalan valid ditemukan di {path}. GeoJSON mungkin kosong atau format salah.")
            # Fallback jika GeoJSON kosong atau tidak valid
            return {"Daerah Tidak Dikenal": ["Jalan Tidak Ditemukan"]}

        print(f"Berhasil memuat {len(area_map)} daerah dari GeoJSON.")
        # Konversi set ke list terurut untuk konsistensi UI
        return {k: sorted(list(v)) for k, v in area_map.items()}

    except FileNotFoundError:
        print(f"ERROR: File GeoJSON tidak ditemukan di {path}. Gunakan data fallback.")
        return {"Daerah Error": ["File GeoJSON tidak ada"]}
    except json.JSONDecodeError:
        print(f"ERROR: File GeoJSON di {path} tidak valid. Gunakan data fallback.")
        return {"Daerah Error": ["Format GeoJSON salah"]}
    except Exception as e:
        print(f"Error tidak terduga saat memuat GeoJSON: {e}. Gunakan data fallback.")
        return {"Daerah Error": ["Error saat baca GeoJSON"]}

# Konstanta waktu
SCHEDULE_TIMES = ["09.00", "12.00", "15.00", "18.00"]


class OrderDialog(QDialog):
    """Dialog pemesanan berukuran 800x600, modal, dengan validasi dan penyimpanan."""

    def __init__(self, parent=None, current_user: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Pemesanan")
        self.resize(800, 600); self.setModal(True)
        self.current_user = current_user or {}
        self.setStyleSheet("""...""") # Stylesheet Anda

        self.items = [] # list of dict: {name, price, qty}

        # [MODIFIKASI] Muat data area/jalan dari GeoJSON saat inisialisasi
        self._area_map = _load_area_streets_from_geojson()
        self._products = _load_products_from_json()

        self._build_ui()
        self._wire_events()
        self._refresh_totals()
        self._prefill_user_info() # [BARU] Isi nama jika ada

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(10)

        title = QLabel("Pemesanan"); title.setObjectName("OrderTitle"); title.setStyleSheet("QLabel#OrderTitle { font-size: 20px; font-weight: 800; color: #0f5b6b; }"); layout.addWidget(title)

        self.input_name = QLineEdit(); self.input_name.setPlaceholderText("Atas Nama (*Wajib)"); layout.addWidget(self.input_name)

        area_row = QHBoxLayout()
        self.combo_area = QComboBox()
        self.combo_area.addItem("-- Pilih Daerah --")
        # [MODIFIKASI] Isi dropdown area dari self._area_map
        for a in sorted(self._area_map.keys()): # Urutkan nama daerah
            self.combo_area.addItem(a)

        self.combo_street = QComboBox()
        self.combo_street.addItem("-- Pilih Jalan/Persimpangan --") # Ganti nama
        self.input_note = QLineEdit(); self.input_note.setPlaceholderText("Keterangan Tambahan (Nomor Rumah, dll.)")
        area_row.addWidget(self.combo_area, 1) # Beri proporsi
        area_row.addWidget(self.combo_street, 2) # Beri proporsi lebih besar
        area_row.addWidget(self.input_note, 1) # Beri proporsi
        row_area_widget = QWidget(); row_area_widget.setLayout(area_row); layout.addWidget(row_area_widget)

        time_row = QHBoxLayout()
        self.combo_mode = QComboBox(); self.combo_mode.addItems(["-- Pilih Mode Pengiriman --", "Pengiriman Segera", "Pengiriman Terjadwal"])
        self.combo_time = QComboBox(); self.combo_time.addItem("-- Pilih Waktu --"); self.combo_time.addItems(SCHEDULE_TIMES); self.combo_time.setEnabled(False)
        time_row.addWidget(self.combo_mode); time_row.addWidget(self.combo_time)
        row_time_widget = QWidget(); row_time_widget.setLayout(time_row); layout.addWidget(row_time_widget)

        product_row = QHBoxLayout()
        self.combo_product = QComboBox()
        self.combo_product.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        lv = QListView(); lv.setMinimumWidth(420); self.combo_product.setView(lv)
        # [MODIFIKASI] Isi dropdown produk dari self._products
        for name, price in self._products.items():
            self.combo_product.addItem(f"{name}\t(Rp {price:,})", userData={"name": name, "price": price}) # Format harga lebih jelas

        self.spin_qty = QSpinBox(); self.spin_qty.setRange(1, 100); self.spin_qty.setMinimumWidth(60) # Lebar minimum
        self.btn_add_item = QPushButton("➕ Tambah"); self.btn_add_item.setStyleSheet("background:#2ecc71;color:white;font-weight:700;padding:6px 12px;border-radius:8px;")
        self.btn_remove_item = QPushButton("➖ Hapus Item"); self.btn_remove_item.setStyleSheet("background:#e74c3c;color:white;font-weight:700;padding:6px 12px;border-radius:8px;")
        product_row.addWidget(self.combo_product, 3); product_row.addWidget(QLabel("Jumlah:")); product_row.addWidget(self.spin_qty, 1); product_row.addWidget(self.btn_add_item); product_row.addWidget(self.btn_remove_item)
        row_product_widget = QWidget(); row_product_widget.setLayout(product_row); layout.addWidget(row_product_widget)

        self.list_items = QListWidget(); self.list_items.setFixedHeight(120) # Kurangi tinggi sedikit
        totals_box = QVBoxLayout(); self.label_total_barang = QLabel("Total Barang: Rp 0"); self.label_total_ongkir = QLabel("Total Biaya Pengiriman: (dihitung nanti)") # Teks default
        totals_box.addWidget(self.label_total_barang); totals_box.addWidget(self.label_total_ongkir)
        totals_widget = QWidget(); totals_widget.setLayout(totals_box)
        items_panel = QFrame(); items_panel.setObjectName("ItemsPanel"); items_panel_layout = QVBoxLayout(items_panel); items_panel_layout.setContentsMargins(12, 12, 12, 12); items_panel_layout.setSpacing(8); items_panel_layout.addWidget(self.list_items); items_panel_layout.addWidget(totals_widget)
        items_panel.setStyleSheet("QFrame#ItemsPanel { background-color: rgba(255, 255, 255, 0.95); border: 1px solid rgba(0,0,0,0.06); border-radius: 12px; }")
        layout.addWidget(items_panel)

        btn_row = QHBoxLayout()
        self.btn_cancel = QPushButton("Batal"); self.btn_cancel.setObjectName("SecondaryButton"); # Beri ID jika perlu style beda
        self.btn_submit = QPushButton("🛒 Pesan Sekarang"); self.btn_submit.setEnabled(False); self.btn_submit.setStyleSheet("background:#2196F3;color:white;font-weight:700;padding:8px 16px;border-radius:8px;")
        btn_row.addWidget(self.btn_cancel); btn_row.addStretch(1); btn_row.addWidget(self.btn_submit) # Pindahkan submit ke kanan
        row_btn_widget = QWidget(); row_btn_widget.setLayout(btn_row); layout.addWidget(row_btn_widget)

    def _wire_events(self):
        self.combo_area.currentIndexChanged.connect(self._on_area_changed)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        self.btn_add_item.clicked.connect(self._on_add_item)
        self.btn_remove_item.clicked.connect(self._on_remove_item)
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_submit.clicked.connect(self._on_submit)
        # Validasi input
        self.input_name.textChanged.connect(self._update_submit_enabled)
        self.combo_area.currentIndexChanged.connect(self._update_submit_enabled)
        self.combo_street.currentIndexChanged.connect(self._update_submit_enabled)
        self.combo_mode.currentIndexChanged.connect(self._update_submit_enabled)
        self.combo_time.currentIndexChanged.connect(self._update_submit_enabled)
        self.list_items.model().rowsInserted.connect(self._update_submit_enabled) # Cek saat item ditambah
        self.list_items.model().rowsRemoved.connect(self._update_submit_enabled) # Cek saat item dihapus

    def _on_area_changed(self, index): # Terima index
        """Update dropdown jalan/persimpangan saat area berubah."""
        self.combo_street.blockSignals(True) # Cegah trigger _update_submit_enabled
        self.combo_street.clear()
        self.combo_street.addItem("-- Pilih Jalan/Persimpangan --")
        if index > 1: # Pastikan bukan pilihan default "-- Pilih Daerah --"
            area = self.combo_area.currentText()
            streets = self._area_map.get(area, [])
            if streets:
                self.combo_street.addItems(streets)
        self.combo_street.blockSignals(False)
        self._update_submit_enabled() # Panggil manual setelah selesai

    def _on_mode_changed(self, index): # Terima index
        if index == 2: # "Pengiriman Terjadwal"
            self.combo_time.setEnabled(True)
        else:
            self.combo_time.setEnabled(False)
            self.combo_time.setCurrentIndex(0) # Reset ke default
        self._update_submit_enabled()

    def _on_add_item(self):
        selected_index = self.combo_product.currentIndex()
        data = self.combo_product.itemData(selected_index)
        if not data:
            QMessageBox.warning(self, "Pilih Produk", "Silakan pilih produk terlebih dahulu.")
            return
        qty = self.spin_qty.value()
        name = data["name"]
        price = data["price"]

        # Cek apakah item sudah ada, jika ya, update qty
        existing_item = next((item for item in self.items if item["name"] == name), None)
        if existing_item:
             existing_item["qty"] += qty
             # Update tampilan di QListWidget
             for i in range(self.list_items.count()):
                 list_item = self.list_items.item(i)
                 # Perlu cara untuk mengidentifikasi item, misal simpan nama di data item
                 if list_item.data(Qt.ItemDataRole.UserRole) == name:
                      item_text = f"{name} x{existing_item['qty']} - Rp{price*existing_item['qty']:,}"
                      list_item.setText(item_text)
                      break
        else:
             self.items.append({"name": name, "price": price, "qty": qty})
             item_text = f"{name} x{qty} - Rp{price*qty:,}"
             list_widget_item = QListWidgetItem(item_text)
             list_widget_item.setData(Qt.ItemDataRole.UserRole, name) # Simpan nama untuk identifikasi
             self.list_items.addItem(list_widget_item)

        self._refresh_totals()
        # _update_submit_enabled() akan dipanggil oleh sinyal rowsInserted/rowsRemoved

    def _on_remove_item(self):
        selected_items = self.list_items.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Pilih Item", "Pilih item pada daftar untuk dihapus.")
            return

        current_item = selected_items[0]
        row = self.list_items.row(current_item)

        # Hapus dari state internal `self.items`
        item_name_to_remove = current_item.data(Qt.ItemDataRole.UserRole) # Ambil nama dari data
        self.items = [item for item in self.items if item["name"] != item_name_to_remove]

        # Hapus dari QListWidget
        self.list_items.takeItem(row)

        self._refresh_totals()
        # _update_submit_enabled() akan dipanggil oleh sinyal rowsInserted/rowsRemoved

    def _refresh_totals(self):
        subtotal = sum(it["price"] * it["qty"] for it in self.items)
        shipping = "Rp ?" # Placeholder
        self.label_total_barang.setText(f"Total Barang: Rp {subtotal:,}")
        self.label_total_ongkir.setText(f"Biaya Pengiriman: {shipping}")

    def _all_inputs_valid(self) -> bool:
        # Pengecekan lebih ketat
        if not self.input_name.text().strip(): return False
        if self.combo_area.currentIndex() <= 0: return False
        if self.combo_street.currentIndex() <= 0: return False
        if not self.items: return False # Cek list items
        if self.combo_mode.currentIndex() <= 0: return False # Cek pilihan mode valid
        if self.combo_mode.currentIndex() == 2 and self.combo_time.currentIndex() <= 0: return False # Cek waktu jika terjadwal
        return True

    def _update_submit_enabled(self):
        """Enable tombol Pesan hanya jika semua input valid."""
        is_valid = self._all_inputs_valid()
        self.btn_submit.setEnabled(is_valid)

    def _warn(self, title: str, text: str) -> bool:
        # Dialog konfirmasi standar
        return QMessageBox.question(self, title, text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Yes

    def _on_cancel(self):
        if self._warn("Batalkan Pemesanan", "Yakin ingin membatalkan? Data akan hilang."):
            self.reject() # Tutup dialog tanpa menyimpan

    def _on_submit(self):
        if not self._all_inputs_valid():
            QMessageBox.warning(self, "Input Belum Lengkap", "Mohon lengkapi semua field yang wajib (*).")
            return
        if not self._warn("Konfirmasi Pesanan", "Kirim pesanan ini?"):
            return

        # Bangun record order
        mode = self.combo_mode.currentText()
        schedule_val = "Segera"
        if mode == "Pengiriman Terjadwal":
            schedule_val = self.combo_time.currentText()

        order = {
            "id": self._generate_order_id(),
            "customer_name": self.input_name.text().strip(),
            "items": [{"name": it["name"], "qty": it["qty"]} for it in self.items],
            # "eta": dihitung nanti oleh seller atau sistem
            "schedule": schedule_val, # 'Segera' atau 'HH.MM'
            "status": "menunggu", # Status awal
            "area": self.combo_area.currentText(),
            "street": self.combo_street.currentText(), # Ini sekarang nama persimpangan/node
            "note": self.input_note.text().strip(),
            "created_at": datetime.datetime.now().isoformat(timespec='seconds'), # Format ISO
            "user_name": self.current_user.get("name"),
            "user_email": self.current_user.get("email"),
            # Tambahkan field lain jika perlu, misal total harga
            "subtotal": sum(it["price"] * it["qty"] for it in self.items)
        }

        try:
            orders = load_orders() or []
            orders.append(order)
            if save_orders(orders):
                QMessageBox.information(self, "Berhasil 👍", "Pesanan Anda berhasil dibuat dan menunggu konfirmasi penjual.")
                self.accept() # Tutup dialog setelah berhasil
            else:
                QMessageBox.critical(self, "Gagal 😥", "Terjadi kesalahan saat menyimpan pesanan.")
        except Exception as e:
             QMessageBox.critical(self, "Error Penyimpanan", f"Gagal menyimpan data: {e}")

    def _generate_order_id(self) -> str:
        # ID Generator (Sudah benar)
        try:
            orders = load_orders() or []
            max_n = 0
            for o in orders:
                oid = o.get("id", "")
                if isinstance(oid, str) and oid.startswith("ORD-"):
                    try: n = int(oid.split("-")[-1]); max_n = max(max_n, n)
                    except Exception: pass
            return f"ORD-{max_n + 1:04d}" # Pakai 4 digit
        except Exception:
            # Fallback jika gagal baca file
            return f"ORD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    # [BARU] Isi nama dari current_user
    def _prefill_user_info(self):
        """Isi field 'Atas Nama' jika ada data pengguna."""
        if self.current_user and self.current_user.get("name"):
            self.input_name.setText(self.current_user["name"])

# --- Akhir Kelas OrderDialog ---