"""
UI_sl_order.py
Halaman Pengantaran untuk Seller (PyQt6)

Menampilkan daftar pesanan yang sedang dalam proses pengantaran/penyiapan:
- Status yang ditampilkan: menunggu (disiapkan), diterima, dalam_perjalanan
- Kartu berisi judul, subjudul (ETA/Jadwal), badge status, dan kebab aksi
"""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QHBoxLayout,
    QPushButton, QMenu, QSizePolicy, QSpacerItem, QMessageBox, QDialog
)
import os, json, datetime

try:
    # Import fungsi logic untuk load/save data pesanan
    from logic.file.order_logic import load_orders, save_orders
    from UI.seller.UI_sl_deliv import DeliveryPreviewDialog
    from UI.seller.UI_sl_Gcoloring import OrderPreviewDialog
except Exception:
    # Fallback jika modul belum tersedia saat dev
    def load_orders():
        return []
    def save_orders(_):
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


class OrderCard(QFrame):
    """Widget kartu pesanan satu baris."""

    def __init__(self, order: dict, parent=None, marker_deleted=None, desc_marker=None):
        super().__init__(parent)
        self.order = order
        self.marker_deleted = marker_deleted
        self.desc_marker = desc_marker
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
        menu.addAction("Antrian").triggered.connect(self._on_queue)
        menu.addAction("Kirim").triggered.connect(self._on_deliver)
        menu.addAction("Selesai").triggered.connect(self._on_done)
        kebab.setMenu(menu)

        # Tombol kebab tetap tersedia kecuali status final (selesai/telah_tiba/ditolak)
        disable_kebab = self._is_final()
        kebab.setEnabled(not disable_kebab)

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
            QPushButton#KebabButton { border: none; background: transparent; font-size: 18px; }
            QPushButton#KebabButton:hover { background: rgba(0,0,0,0.05); border-radius: 6px; }
            """
        )

    def _update_order_status(self, new_status: str):
        """Update status order di order_data.json lalu refresh tampilan."""
        order_id = self.order.get("id")
        if not order_id:
            return
        orders = load_orders() or []
        updated = False
        for o in orders:
            if o.get("id") == order_id:
                o["status"] = new_status
                updated = True
                break
        if updated and save_orders(orders):
            parent = self.parent()
            while parent and not isinstance(parent, SellerDeliveryPage):
                parent = parent.parent()
            if isinstance(parent, SellerDeliveryPage):
                parent.reload_orders()

    def _confirm(self, title: str, text: str) -> bool:
        res = QMessageBox.question(self, title, text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return res == QMessageBox.StandardButton.Yes

    def _on_queue(self):
        """Set status menjadi 'menunggu' (masuk antrian)."""
        if self._confirm("Konfirmasi Antrian", "Apakah Anda yakin memindahkan pesanan ke Antrian (menunggu)?"):
            self._update_order_status("menunggu")

    def _on_deliver(self):
        """Set status menjadi 'dalam_perjalanan' (dalam pengantaran)."""
        # Tampilkan dialog preview terlebih dahulu
        try:
            dlg = DeliveryPreviewDialog(self.order, marker_deleted=self.marker_deleted, parent=self, desc_marker=self.desc_marker)
            res = dlg.exec()
            if res == QDialog.DialogCode.Accepted:
                self._update_order_status("dalam_perjalanan")
        except Exception:
            # Fallback ke konfirmasi lama jika dialog gagal
            if self._confirm("Konfirmasi Pengantaran", "Apakah Anda yakin memulai pengantaran untuk pesanan ini?"):
                self._update_order_status("dalam_perjalanan")

    def _on_done(self):
        """Set status menjadi 'selesai' (pesanan selesai)."""
        if self._confirm("Konfirmasi Selesai", "Tandai pesanan ini sebagai Selesai?"):
            order_id = self.order.get("id")
            if not order_id:
                return
            orders = load_orders() or []
            done = None
            remaining = []
            for o in orders:
                if o.get("id") == order_id:
                    done = dict(o)
                else:
                    remaining.append(o)
            if done is None:
                return
            # Tandai final dan waktu selesai
            done["status"] = "selesai"
            done["finalized_at"] = datetime.datetime.now().isoformat()
            # Simpan ke history customer (dan seller optional)
            _append_json_list(_db_path('customer_history.json'), done)
            try:
                _append_json_list(_db_path('seller_history.json'), done)
            except Exception:
                pass
            # Hapus dari orders aktif
            if save_orders(remaining):
                parent = self.parent()
                while parent and not isinstance(parent, SellerDeliveryPage):
                    parent = parent.parent()
                if isinstance(parent, SellerDeliveryPage):
                    parent.reload_orders()

    def _on_reject(self):
        """Tolak pesanan: pindahkan ke history customer dan seller lalu hapus dari order aktif."""
        order_id = self.order.get("id")
        if not order_id:
            return
        orders = load_orders() or []
        rejected = None
        remaining = []
        for o in orders:
            if o.get("id") == order_id:
                rejected = dict(o)
            else:
                remaining.append(o)
        if rejected is None:
            return
        # Tandai status final
        rejected["status"] = "ditolak"
        rejected["finalized_at"] = datetime.datetime.now().isoformat()
        # Simpan ke histories
        customer_hist_path = _db_path('customer_history.json')
        seller_hist_path = _db_path('seller_history.json')
        _append_json_list(customer_hist_path, rejected)
        _append_json_list(seller_hist_path, rejected)
        # Hapus dari order aktif
        if save_orders(remaining):
            parent = self.parent()
            while parent and not isinstance(parent, CustomerDashboard):
                parent = parent.parent()
            if isinstance(parent, CustomerDashboard):
                parent.reload_orders()

    def _build_title_text(self) -> str:
        """Judul: Nama customer + (akun)."""
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

    def _is_final(self) -> bool:
        """True jika status final (tidak bisa diubah via kebab)."""
        order_status = self.order.get("status", "menunggu")
        return order_status in {"telah_tiba", "selesai", "ditolak"}


class SellerDeliveryPage(QWidget):
    """Halaman Pengantaran seller: menampilkan list kartu pesanan terpilih."""

    def __init__(self, parent=None, current_user: dict | None = None, marker_deleted=None, desc_marker=None):
        super().__init__(parent)
        self._orders = []
        self.current_user = current_user or {}
        self.marker_deleted=marker_deleted
        self.desc_marker = desc_marker
        self._build_ui()
        self.reload_orders()

    def _build_ui(self):
        """Bangun layout dasar: judul + scroll area berisi kartu."""
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Pengantaran")
        title.setObjectName("PageTitle")
        title.setStyleSheet("QLabel#PageTitle { font-size: 20px; font-weight: 800; color: #0f5b6b; }")

        self.btn_preview_orderan = QPushButton()
        self.btn_preview_orderan.setText("Preview Orderan")
        self.btn_preview_orderan.setStyleSheet("""
            QPushButton {
                background: #F8FFFF;
                color: #2196F3;
                font-weight: 700; 
                padding: 10px 18px; 
                border-radius: 8px; 
                border: 2px solid #2196F3;
            }
            QPushButton:hover {
                background-color: #97C9F5;
            }
        """)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(10)
        self.scroll.setWidget(self.container)

        self.title_layout = QHBoxLayout()
        self.title_layout.addWidget(title)
        self.title_layout.addStretch(5)
        self.title_layout.addWidget(self.btn_preview_orderan)
        root.addLayout(self.title_layout)
        root.addWidget(self.scroll)

        self.setStyleSheet(
            """
            QWidget { background: #ffffff; }
            QScrollArea { background: transparent; }
            """
        )

        # Events
        try:
            self.btn_preview_orderan.clicked.connect(self._on_open_order_preview_dialog)
        except Exception:
            pass

    def reload_orders(self):
        """Muat ulang data pesanan dan tampilkan hanya status tertentu untuk pengantaran."""
        all_orders = load_orders() or []
        allowed = {"sedang_disiapkan", "dalam_perjalanan", "telah_tiba"}
        self._orders = [o for o in all_orders if (o.get("status") or "").strip().lower() in allowed]
        # Bersihkan container
        for i in reversed(range(self.container_layout.count())):
            item = self.container_layout.takeAt(i)
            w = item.widget()
            if w:
                w.setParent(None)

        # Tambah kartu untuk tiap order
        for order in self._orders:
            self.container_layout.addWidget(OrderCard(order, marker_deleted=self.marker_deleted, desc_marker=self.desc_marker))

        # Tambah spacer agar list tidak terlalu rapat bawah
        self.container_layout.addStretch(1)

    def set_current_user(self, user: dict | None):
        """Setter current user lalu reload tampilan."""
        self.current_user = user or {}
        self.reload_orders()

    def _on_open_order_preview_dialog(self):
        try:
            dlg = OrderPreviewDialog(self)
            dlg.exec()
        except Exception:
            pass

