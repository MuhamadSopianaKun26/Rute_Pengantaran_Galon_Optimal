"""
UI_cs_dashboard.py
Halaman Dashboard untuk Customer (PyQt6)

Menampilkan daftar pesanan dalam bentuk kartu:
- Judul (nama produk/nama pesanan)
- Subjudul kecil (ETA/Jam estimasi dan jadwal/pesan untuk pukul)
- Badge status di sisi kanan: (keranjang, menunggu, diterima, dalam_perjalanan, telah_tiba, selesai)
- Tombol tiga titik (kebab) untuk Edit/Hapus, nonaktif jika status sudah > diterima
"""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QHBoxLayout,
    QPushButton, QMenu, QSizePolicy, QSpacerItem, QMessageBox
)
import os, json, datetime

try:
    # Import fungsi logic untuk load/save data pesanan
    from logic.file.order_logic import load_orders, save_orders
except Exception:
    # Fallback jika modul belum tersedia saat dev
    def load_orders():
        return []
    def save_orders(_):
        return False

try:
    # Dialog order untuk edit
    from .UI_cs_order import OrderDialog
except Exception:
    try:
        from UI.customer.UI_cs_order import OrderDialog
    except Exception:
        OrderDialog = None


def _db_path(filename: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, 'Database', filename)

def _append_json_list(file_path: str, record: dict) -> bool:
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = []
        if not isinstance(data, list):
            data = []
        data.append(record)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


STATUS_STYLES = {
    # mapping status -> (label tampil, warna latar, warna teks)
    "keranjang": ("Keranjang", "#ECEFF1", "#37474F"),
    "menunggu": ("Menunggu", "#FFF3E0", "#E65100"),
    "diterima": ("Diterima", "#E3F2FD", "#1565C0"),
    "dalam_perjalanan": ("Dalam Pengantaran", "#E0F7FA", "#006064"),
    "telah_tiba": ("Telah Tiba", "#E8F5E9", "#1B5E20"),
    "selesai": ("Selesai", "#F1F8E9", "#33691E"),
    "ditolak": ("Ditolak", "#FFEBEE", "#D32F2F"),
    "sedang_disiapkan": ("Sedang Disiapkan", "#FFFDE7", "#8D6E63"),
    "dibatalkan": ("Dibatalkan", "#FFEBEE", "#C62828"),
}


class OrderCard(QFrame):
    """Widget kartu pesanan satu baris."""

    def __init__(self, order: dict, parent=None):
        super().__init__(parent)
        self.order = order
        self.setObjectName("OrderCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._build_ui()

    def _build_ui(self):
        """Bangun UI kartu pesanan."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Kiri: judul dan daftar barang (ordered list)
        left_box = QVBoxLayout()
        left_box.setSpacing(6)

        title = QLabel(self._build_title_text())
        title.setObjectName("OrderTitle")
        title.setWordWrap(True)

        items_list = QLabel(self._build_items_ordered_list())
        items_list.setObjectName("OrderItems")
        items_list.setWordWrap(True)

        left_box.addWidget(title)
        left_box.addWidget(items_list)

        # Spacer di tengah
        layout.addLayout(left_box)
        layout.addItem(QSpacerItem(20, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Kanan: info tambahan + badge status + kebab menu
        right_box = QHBoxLayout()
        right_box.setSpacing(12)

        info_box = QVBoxLayout()
        info_box.setSpacing(2)
        lbl_addr = QLabel(self._build_address_text())
        lbl_addr.setObjectName("OrderAddr")
        lbl_addr.setWordWrap(True)
        lbl_created = QLabel(self._build_created_text())
        lbl_created.setObjectName("OrderCreated")
        lbl_eta = QLabel(self._build_eta_text())
        lbl_eta.setObjectName("OrderETA")
        lbl_mode = QLabel(self._build_mode_text())
        lbl_mode.setObjectName("OrderMode")
        info_box.addWidget(lbl_addr)
        info_box.addWidget(lbl_created)
        info_box.addWidget(lbl_eta)
        info_box.addWidget(lbl_mode)
        right_box.addLayout(info_box)

        status_label = self._build_status_badge()
        right_box.addWidget(status_label, 0, Qt.AlignmentFlag.AlignRight)

        kebab = QPushButton("⋯")
        kebab.setObjectName("KebabButton")
        kebab.setFixedSize(QSize(36, 28))
        kebab.setCursor(Qt.CursorShape.PointingHandCursor)
        menu = QMenu(self)
        menu.addAction("Edit").triggered.connect(self._on_edit)
        menu.addAction("Batalkan").triggered.connect(self._on_cancel)
        kebab.setMenu(menu)

        # Nonaktifkan kebab jika status sudah >= diterima
        disable_kebab = self._is_after_received()
        kebab.setEnabled(not disable_kebab)
        kebab.setVisible(True if not disable_kebab else False)

        right_box.addWidget(kebab, 0, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(right_box)

        # Styling
        self.setStyleSheet(
            """
            #OrderCard {
                background: white;
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 12px;
            }
            QLabel#OrderTitle { font-size: 16px; font-weight: 700; color: #0f5b6b; }
            QLabel#OrderSubtitle { font-size: 12px; color: #3b6a75; }
            QPushButton#KebabButton { border: none; background: transparent; font-size: 18px; }
            QPushButton#KebabButton:hover { background: rgba(0,0,0,0.05); border-radius: 6px; }
            """
        )

    def _on_edit(self):
        """Edit pesanan: buka OrderDialog dengan data terisi, lalu simpan perubahan menggantikan data lama."""
        if OrderDialog is None:
            QMessageBox.warning(self, "Edit Tidak Tersedia", "Form pemesanan tidak tersedia.")
            return
        # Cari parent window untuk mengambil current_user
        parent = self.parent()
        while parent and not isinstance(parent, CustomerDashboard):
            parent = parent.parent()
        current_user = getattr(parent, 'current_user', {}) if isinstance(parent, CustomerDashboard) else {}
        dlg = OrderDialog(self, current_user=current_user)
        # Prefill fields dari order
        try:
            self._prefill_dialog(dlg, self.order)
        except Exception:
            pass
        if dlg.exec():
            # Build updated order dari dialog state (gunakan fungsi submit-nya)
            # Kita re-bangun minimal field dari dialog
            updated = {
                "id": self.order.get("id"),
                "customer_name": dlg.input_name.text().strip(),
                "items": [{"name": d["name"], "qty": d["qty"]} for d in getattr(dlg, 'items', [])],
                "eta": dlg.combo_time.currentText() if dlg.combo_mode.currentText()=="Pengiriman Terjadwal" else "-",
                "schedule": dlg.combo_time.currentText() if dlg.combo_mode.currentText()=="Pengiriman Terjadwal" else "Segera",
                "status": self.order.get("status", "menunggu"),
                "area": dlg.combo_area.currentText(),
                "street": dlg.combo_street.currentText(),
                "note": dlg.input_note.text().strip(),
                "created_at": self.order.get("created_at"),
                "user_name": self.order.get("user_name"),
                "user_email": self.order.get("user_email"),
            }
            orders = load_orders() or []
            for i, o in enumerate(orders):
                if o.get("id") == updated["id"]:
                    orders[i] = updated
                    break
            if save_orders(orders):
                # Refresh
                if isinstance(parent, CustomerDashboard):
                    parent.reload_orders()
            else:
                QMessageBox.critical(self, "Gagal", "Gagal memperbarui pesanan.")

    def _on_cancel(self):
        """Batalkan pesanan: ubah status ke 'dibatalkan', pindahkan ke history customer, dan hapus dari order aktif."""
        if QMessageBox.question(self, "Konfirmasi Batalkan", "Apakah Anda yakin ingin membatalkan pesanan ini?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        order_id = self.order.get("id")
        if not order_id:
            return
        orders = load_orders() or []
        canceled = None
        remaining = []
        for o in orders:
            if o.get("id") == order_id:
                canceled = dict(o)
            else:
                remaining.append(o)
        if canceled is None:
            return
        canceled["status"] = "dibatalkan"
        canceled["canceled_at"] = datetime.datetime.now().isoformat()
        canceled["finalized_at"] = canceled.get("finalized_at") or canceled["canceled_at"]
        # Tulis ke history customer
        _append_json_list(_db_path('customer_history.json'), canceled)
        # Simpan kembali orders tanpa yang dibatalkan
        if save_orders(remaining):
            parent = self.parent()
            while parent and not isinstance(parent, CustomerDashboard):
                parent = parent.parent()
            if isinstance(parent, CustomerDashboard):
                parent.reload_orders()

    def _build_title_text(self) -> str:
        """Judul: Nama customer + (akun)"""
        name = self.order.get("customer_name", "-")
        account = self.order.get("user_email") or self.order.get("user_name") or "-"
        return f"{name} ({account})"

    def _build_items_ordered_list(self) -> str:
        """Daftar barang sebagai ordered list ke bawah."""
        items = self.order.get("items", [])
        lines = []
        if items and isinstance(items[0], dict):
            for idx, it in enumerate(items, start=1):
                nm = it.get("name", "Produk")
                qty = it.get("qty", 1)
                lines.append(f"{idx}. {nm} x{qty}")
        else:
            for idx, nm in enumerate(items, start=1):
                lines.append(f"{idx}. {nm}")
        return "\n".join(lines) if lines else "-"

    def _build_address_text(self) -> str:
        area = self.order.get("area") or "-"
        street = self.order.get("street") or "-"
        return f"Alamat: {area} - {street}"

    def _build_created_text(self) -> str:
        return f"Dibuat: {self._fmt_dt(self.order.get('created_at'))}"

    def _build_eta_text(self) -> str:
        eta = self.order.get("eta") or "-"
        return f"Estimasi Sampai: {eta}"

    def _build_mode_text(self) -> str:
        schedule = self.order.get("schedule") or "Segera"
        mode = "Segera" if schedule == "Segera" else f"Terjadwal {{{schedule}}}"
        return f"Tipe: {mode}"

    def _build_status_badge(self) -> QLabel:
        """Buat badge status berwarna sesuai mapping."""
        status = self.order.get("status", "menunggu")
        label_text, bg, fg = STATUS_STYLES.get(status, (status.title(), "#ECEFF1", "#37474F"))
        badge = QLabel(label_text)
        badge.setObjectName("StatusBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedHeight(28)
        badge.setStyleSheet(
            f"""
            QLabel#StatusBadge {{
                background: {bg};
                color: {fg};
                border-radius: 8px;
                padding: 4px 10px;
                min-width: 120px;
                font-weight: 700;
                font-size: 12px;
            }}
            """
        )
        return badge

    def _fmt_dt(self, value) -> str:
        s = value or ""
        if not s:
            return "-"
        fmts = [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
        ]
        dt = None
        for f in fmts:
            try:
                dt = datetime.datetime.strptime(s, f)
                break
            except Exception:
                continue
        if dt is None:
            try:
                dt = datetime.datetime.fromisoformat(s)
            except Exception:
                return s
        return dt.strftime("%d-%m-%Y %H:%M:%S")

    def _prefill_dialog(self, dlg, order: dict):
        """Prefill OrderDialog berdasarkan data order lama."""
        # Nama
        if hasattr(dlg, 'input_name'):
            dlg.input_name.setText(order.get('customer_name', ''))
        # Area dan jalan
        if hasattr(dlg, 'combo_area'):
            area = order.get('area') or ''
            idx = dlg.combo_area.findText(area)
            if idx >= 0:
                dlg.combo_area.setCurrentIndex(idx)
        if hasattr(dlg, 'combo_street'):
            street = order.get('street') or ''
            # Pastikan daftar jalan sudah terisi setelah area dipilih
            idx_s = dlg.combo_street.findText(street)
            if idx_s >= 0:
                dlg.combo_street.setCurrentIndex(idx_s)
        # Note
        if hasattr(dlg, 'input_note'):
            dlg.input_note.setText(order.get('note', ''))
        # Mode dan waktu terjadwal
        if hasattr(dlg, 'combo_mode') and hasattr(dlg, 'combo_time'):
            schedule = order.get('schedule') or 'Segera'
            if schedule and schedule != 'Segera':
                idx_m = dlg.combo_mode.findText('Pengiriman Terjadwal')
                if idx_m >= 0:
                    dlg.combo_mode.setCurrentIndex(idx_m)
                # enable time combo jika perlu sudah ditangani handler di dialog
                idx_t = dlg.combo_time.findText(schedule)
                if idx_t >= 0:
                    dlg.combo_time.setCurrentIndex(idx_t)
            else:
                idx_m = dlg.combo_mode.findText('-- Pilih Mode --')
                if idx_m >= 0:
                    dlg.combo_mode.setCurrentIndex(idx_m)
        # Items
        if hasattr(dlg, 'items') and hasattr(dlg, 'list_items'):
            dlg.items = []
            dlg.list_items.clear()
            for it in order.get('items', []):
                name = it.get('name') if isinstance(it, dict) else str(it)
                qty = it.get('qty') if isinstance(it, dict) else 1
                dlg.items.append({'name': name, 'price': 0, 'qty': qty})
                # Tampilkan ringkas di list
                try:
                    from PyQt6.QtWidgets import QListWidgetItem
                    dlg.list_items.addItem(QListWidgetItem(f"{name} x{qty}"))
                except Exception:
                    pass
            # Refresh total agar label update
            if hasattr(dlg, '_refresh_totals'):
                try:
                    dlg._refresh_totals()
                except Exception:
                    pass
    def _is_after_received(self) -> bool:
        """Tentukan apakah status sudah di tahap setelah 'diterima'."""
        order_status = self.order.get("status", "menunggu")
        order_flow = ["keranjang", "menunggu", "diterima", "dalam_perjalanan", "telah_tiba", "selesai"]
        try:
            idx = order_flow.index(order_status)
            return idx >= order_flow.index("diterima")
        except ValueError:
            return False


class CustomerDashboard(QWidget):
    """Halaman Dashboard utama customer: menampilkan list kartu pesanan."""

    def __init__(self, parent=None, current_user: dict | None = None):
        super().__init__(parent)
        self._orders = []
        self.current_user = current_user or {}
        self._build_ui()
        self.reload_orders()

    def _build_ui(self):
        """Bangun layout dasar: judul + scroll area berisi kartu."""
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Dashboard Pesanan")
        title.setObjectName("PageTitle")
        title.setStyleSheet("QLabel#PageTitle { font-size: 20px; font-weight: 800; color: #0f5b6b; }")

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(10)
        self.scroll.setWidget(self.container)

        root.addWidget(title)
        root.addWidget(self.scroll)

        self.setStyleSheet(
            """
            QWidget { background: #ffffff; }
            QScrollArea { background: transparent; }
            """
        )

    def reload_orders(self):
        """Muat ulang data pesanan dari storage dan render kartu-kartu, difilter per user."""
        all_orders = load_orders() or []
        # Filter berdasarkan user_email atau fallback ke nama customer
        u_email = (self.current_user.get("email") or "").strip().lower()
        u_name = (self.current_user.get("name") or "").strip().lower()
        def _match(o: dict) -> bool:
            email = (o.get("user_email") or "").strip().lower()
            name = (o.get("user_name") or o.get("customer_name") or "").strip().lower()
            if u_email:
                return email == u_email
            if u_name:
                return name == u_name
            return True
        self._orders = [o for o in all_orders if _match(o)]
        # Bersihkan container
        for i in reversed(range(self.container_layout.count())):
            item = self.container_layout.takeAt(i)
            w = item.widget()
            if w:
                w.setParent(None)

        # Tambah kartu untuk tiap order
        for order in self._orders:
            self.container_layout.addWidget(OrderCard(order))

        # Tambah spacer agar list tidak terlalu rapat bawah
        self.container_layout.addStretch(1)

    def set_current_user(self, user: dict | None):
        """Setter current user lalu reload tampilan."""
        self.current_user = user or {}
        self.reload_orders()

