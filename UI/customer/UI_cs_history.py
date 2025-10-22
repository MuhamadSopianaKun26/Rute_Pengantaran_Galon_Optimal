"""
UI_cs_history.py
Halaman History (PyQt6) menampilkan riwayat pesanan yang dibatalkan dan selesai.

Sumber data: Database/customer_history.json (via logic.file.history_logic)
"""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QHBoxLayout,
    QSizePolicy, QSpacerItem
)
import datetime

try:
    # Import logic untuk load history
    from logic.file.history_logic import load_history
except Exception:
    def load_history():
        return []


STATUS_STYLES = {
    # mapping status -> (label tampil, bg, fg)
    "diterima": ("Diterima", "#E3F2FD", "#1565C0"),
    "selesai": ("Selesai", "#F1F8E9", "#33691E"),
    "telah_tiba": ("Telah Tiba", "#E8F5E9", "#1B5E20"),
    "ditolak": ("Ditolak", "#FFEBEE", "#C62828"),
    "dibatalkan": ("Dibatalkan", "#FFEBEE", "#C62828"),
}


class HistoryCard(QFrame):
    """Widget kartu untuk satu record riwayat, dengan desain OrderCard."""

    def __init__(self, rec: dict, parent=None):
        super().__init__(parent)
        self.rec = rec
        self.setObjectName("OrderCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._build_ui()

    def _build_ui(self):
        """Bangun UI kartu riwayat: kiri (judul + items) dan kanan (info + status)."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Kiri: judul dan daftar barang
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

        layout.addLayout(left_box)
        layout.addItem(QSpacerItem(20, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Kanan: info tambahan + badge status
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

        layout.addLayout(right_box)

        # Styling kartu sama dengan OrderCard
        self.setStyleSheet(
            """
            #OrderCard {
                background: white;
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 12px;
            }
            QLabel#OrderTitle { font-size: 16px; font-weight: 700; color: #0f5b6b; }
            QLabel#OrderSubtitle { font-size: 12px; color: #3b6a75; }
            """
        )

    def _build_title_text(self) -> str:
        """Judul: Nama customer + (akun)."""
        name = self.rec.get("customer_name", "-")
        account = self.rec.get("user_email") or self.rec.get("user_name") or "-"
        return f"{name} ({account})"

    def _build_items_ordered_list(self) -> str:
        items = self.rec.get("items", [])
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
        area = self.rec.get("area") or "-"
        street = self.rec.get("street") or "-"
        return f"Alamat: {area} - {street}"

    def _build_created_text(self) -> str:
        return f"Dibuat: {self._fmt_dt(self.rec.get('created_at'))}"

    def _build_eta_text(self) -> str:
        eta = self.rec.get("eta") or "-"
        return f"Estimasi Sampai: {eta}"

    def _build_mode_text(self) -> str:
        schedule = self.rec.get("schedule") or "Segera"
        mode = "Segera" if schedule == "Segera" else f"Terjadwal {{{schedule}}}"
        return f"Tipe: {mode}"

    def _build_status_badge(self) -> QLabel:
        """Buat badge status dari mapping STATUS_STYLES (gaya OrderCard)."""
        status = self.rec.get("status", "selesai")
        text, bg, fg = STATUS_STYLES.get(status, (status.title(), "#ECEFF1", "#37474F"))
        badge = QLabel(text)
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


class CustomerHistory(QWidget):
    """Halaman History: menampilkan list kartu riwayat dari JSON."""

    def __init__(self, parent=None, current_user: dict | None = None):
        super().__init__(parent)
        self._records = []
        self.current_user = current_user or {}
        self._build_ui()
        self.reload_history()

    def _build_ui(self):
        """Bangun layout dasar history: judul + scroll list."""
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Riwayat Pemesanan")
        title.setObjectName("HistPageTitle")
        title.setStyleSheet("QLabel#HistPageTitle { font-size: 20px; font-weight: 800; color: #0f5b6b; }")

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

    def reload_history(self):
        """Muat ulang data riwayat sesuai user saat ini dan status final yang diizinkan."""
        all_records = load_history() or []
        u_email = (self.current_user.get("email") or "").strip().lower()
        u_name = (self.current_user.get("name") or "").strip().lower()
        allowed = {"diterima", "selesai", "telah_tiba", "ditolak", "dibatalkan"}
        def _match(r: dict) -> bool:
            email = (r.get("user_email") or "").strip().lower()
            name = (r.get("user_name") or r.get("customer_name") or "").strip().lower()
            status = (r.get("status") or "").strip().lower()
            if u_email:
                user_ok = email == u_email
            elif u_name:
                user_ok = name == u_name
            else:
                user_ok = True
            return user_ok and status in allowed
        self._records = [r for r in all_records if _match(r)]
        # Bersihkan container
        for i in reversed(range(self.container_layout.count())):
            item = self.container_layout.takeAt(i)
            w = item.widget()
            if w:
                w.setParent(None)

        # Render record
        for rec in self._records:
            self.container_layout.addWidget(HistoryCard(rec))

        self.container_layout.addStretch(1)


def create_history_page(parent: QWidget | None = None) -> CustomerHistory:
    """Factory untuk membuat halaman history (digunakan jika diimport dari tempat lain)."""
    return CustomerHistory(parent)
