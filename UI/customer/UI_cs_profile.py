"""
UI_cs_profile.py
Halaman Profile Customer (PyQt6)
- Avatar lebih besar tanpa outline, di kanan terdapat username (besar, tebal), akun/email (normal), dan role
- Alamat: dropdown wilayah, dropdown nama jalan (dependent), QLineEdit keterangan tambahan, tombol Simpan
- Membaca wilayah dari Database/areas.json dan data user dari Database/user_acc.json
- Menyimpan alamat kembali ke Database/user_acc.json untuk user yang sesuai
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit, QFrame, QPushButton, QMessageBox
import os, json


def _db_path(filename: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, 'Database', filename)

def _graph_path(filename: str) -> str:
    """Bangun path file graph (geojson, cache) di folder logic/graph/"""
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, 'logic', 'graph', filename)


def _load_areas_from_json() -> dict:
    fallback = {
        "Ciwaruga": ["Jl. Ciwaruga 1", "Jl. Ciwaruga 2"],
        "Sarijadi raya": ["Jl. Sarijadi Raya 1", "Jl. Sarijadi Raya 2"],
        "Gerlong hilir": ["Jl. Gerlong Hilir 1", "Jl. Gerlong Hilir 2"],
    }
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
        return areas or fallback
    except Exception:
        return fallback

def _load_area_streets_from_geojson() -> dict:
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
        if area_map:
            return {k: sorted(v) for k, v in area_map.items()}
        return _load_areas_from_json()
    except Exception:
        try:
            return _load_areas_from_json()
        except Exception:
            return {}


class CustomerProfile(QWidget):
    def __init__(self, parent=None, current_user: dict | None = None):
        super().__init__(parent)
        self.current_user = current_user or {}
        self._area_map = _load_area_streets_from_geojson()
        self._user_record = self._load_user_record()
        self._build_ui()
        self._prefill_address()

    def _load_user_record(self) -> dict:
        """Cari user di user_acc.json berdasarkan email (prioritas) lalu nama."""
        path = _db_path('user_acc.json')
        email = (self.current_user.get('email') or '').strip().lower()
        name = (self.current_user.get('name') or '').strip().lower()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = []
        # user_acc.json bisa berupa list of users
        if isinstance(data, dict):
            users = data.get('users', [])
        else:
            users = data
        def norm(s):
            return (s or '').strip().lower()
        for u in users:
            if email and norm(u.get('email')) == email:
                return u
        for u in users:
            if name and norm(u.get('name')) == name:
                return u
        return {}

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header: avatar besar + info user di kanan
        header = QHBoxLayout()
        header.setContentsMargins(12, 0, 0, 0)  # geser sedikit ke kanan
        header.setSpacing(14)  # jarak avatar dengan info di kanan
        avatar = QLabel("👤")
        avatar.setFixedSize(92, 92)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("font-size: 56px; background: transparent; border: none;")

        info_box = QVBoxLayout()
        info_box.setSpacing(2)  # jarak antar label diperkecil
        name = self._user_record.get("name") or self.current_user.get("name") or "User"
        email = self._user_record.get("email") or self.current_user.get("email") or "-"
        role = self._user_record.get("role") or "-"
        self.label_name = QLabel(name)
        self.label_name.setStyleSheet("font-size:22px; font-weight:800; color:#0f5b6b;")
        self.label_email = QLabel(email)
        self.label_email.setStyleSheet("font-size:14px; color:#365a60;")
        self.label_role = QLabel(f"Role: {role}")
        self.label_role.setStyleSheet("font-size:12px; color:#5c7a80;")
        info_box.addWidget(self.label_name)
        info_box.addWidget(self.label_email)
        info_box.addWidget(self.label_role)

        header.addWidget(avatar)
        header.addLayout(info_box)
        header_wrap = QWidget()
        header_wrap.setLayout(header)
        root.addWidget(header_wrap)

        # Address panel
        addr_panel = QFrame()
        addr_panel.setObjectName("AddrPanel")
        addr_panel.setStyleSheet(
            """
            QFrame#AddrPanel {
                background-color: rgba(255,255,255,0.95);
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 12px;
            }
            QComboBox, QLineEdit { font-size: 14px; }
            """
        )
        addr_v = QVBoxLayout(addr_panel)
        addr_v.setContentsMargins(12, 12, 12, 12)
        addr_v.setSpacing(8)

        # Address fields (tanpa label 'Alamat')
        self.combo_area = QComboBox()
        self.combo_area.addItem("-- Pilih Wilayah --")
        for a in sorted(self._area_map.keys()):
            self.combo_area.addItem(a)

        self.combo_street = QComboBox()
        self.combo_street.addItem("-- Pilih Jalan --")
        self.combo_area.currentIndexChanged.connect(self._on_area_changed)

        self.input_note = QLineEdit()
        self.input_note.setPlaceholderText("nomor rumah, warna rumah, dll...")

        addr_v.addWidget(self.combo_area)
        addr_v.addWidget(self.combo_street)
        addr_v.addWidget(self.input_note)

        # Buttons row: Clear (kiri) dan Simpan (kanan dari clear)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setStyleSheet("background:#bdc3c7;color:#2c3e50;font-weight:600;padding:8px 12px;border-radius:8px;")
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_save = QPushButton("Simpan")
        self.btn_save.setStyleSheet("background:#2ecc71;color:white;font-weight:700;padding:8px 14px;border-radius:8px;")
        self.btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self.btn_clear)
        btn_row.addWidget(self.btn_save)
        btn_row_widget = QWidget()
        btn_row_widget.setLayout(btn_row)
        addr_v.addWidget(btn_row_widget)

        root.addWidget(addr_panel)

    def _on_area_changed(self):
        self.combo_street.clear()
        self.combo_street.addItem("-- Pilih Jalan --")
        area = self.combo_area.currentText()
        for s in self._area_map.get(area, []):
            self.combo_street.addItem(s)

    def _prefill_address(self):
        """Prefill alamat dari user_acc.json jika tersedia."""
        area = self._user_record.get('area') or self._user_record.get('address_area')
        street = self._user_record.get('street') or self._user_record.get('address_street')
        note = self._user_record.get('address_note') or ''
        if area and area in self._area_map:
            idx = self.combo_area.findText(area)
            if idx >= 0:
                self.combo_area.setCurrentIndex(idx)
                # trigger load streets
                self._on_area_changed()
        if street:
            idxs = self.combo_street.findText(street)
            if idxs >= 0:
                self.combo_street.setCurrentIndex(idxs)
        if note:
            self.input_note.setText(note)

    def _write_user_address(self, area: str, street: str, note: str) -> bool:
        """Write address to user_acc.json for matched user. Return True if success."""
        path = _db_path('user_acc.json')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = []
        users = data.get('users') if isinstance(data, dict) else (data if isinstance(data, list) else [])
        def norm(s):
            return (s or '').strip().lower()
        email = norm(self.current_user.get('email'))
        name = norm(self.current_user.get('name'))
        updated = False
        for u in users:
            if (email and norm(u.get('email')) == email) or (name and norm(u.get('name')) == name):
                u['area'] = area
                u['street'] = street
                u['address_note'] = note
                updated = True
                break
        if not updated and isinstance(data, list):
            return False
        # Write back
        try:
            if isinstance(data, dict):
                data['users'] = users
                to_write = data
            else:
                to_write = users
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(to_write, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def _on_save(self):
        """Simpan alamat ke Database/user_acc.json pada user yang sesuai."""
        area = self.combo_area.currentText()
        street = self.combo_street.currentText()
        note = self.input_note.text().strip()
        if area.startswith("--") or street.startswith("--"):
            QMessageBox.warning(self, "Validasi", "Pilih wilayah dan jalan terlebih dahulu.")
            return
        ok = self._write_user_address(area, street, note)
        if ok:
            QMessageBox.information(self, "Tersimpan", "Alamat berhasil disimpan.")
        else:
            QMessageBox.warning(self, "User Tidak Ditemukan", "Data pengguna tidak ditemukan atau gagal menyimpan.")

    def _on_clear(self):
        """Kosongkan alamat dan simpan ke database."""
        self.combo_area.setCurrentIndex(0)
        self.combo_street.clear()
        self.combo_street.addItem("-- Pilih Jalan --")
        self.input_note.clear()
        # Simpan kosongkan alamat ke DB (nilai kosong)
        ok = self._write_user_address("", "", "")
        if ok:
            QMessageBox.information(self, "Dikosongkan", "Alamat berhasil dikosongkan.")
        else:
            QMessageBox.warning(self, "User Tidak Ditemukan", "Gagal mengosongkan alamat: user tidak ditemukan.")

