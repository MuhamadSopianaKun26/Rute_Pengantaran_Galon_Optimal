"""
UI_sl_simulation.py
Halaman Simulasi (PyQt6) – menampilkan peta dan kontrol untuk memanipulasi node/edge.
"""

import os
import json
from PyQt6.QtCore import Qt, QUrl, pyqtSlot, QObject
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QComboBox, QPushButton, QSizePolicy, QSpacerItem
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel

class SellerSimulation(QWidget):
    def __init__(self, parent=None, current_user: dict | None = None):
        super().__init__(parent)
        self.current_user = current_user or {}
        self.map_loaded = False

        # --- Setup Web View ---
        self.web_view = QWebEngineView()
        self.channel = QWebChannel()
        self.web_view.page().setWebChannel(self.channel)
        self.web_view.loadFinished.connect(self.on_load_finished)

        # --- Inisialisasi UI dan Data ---
        self._init_ui()
        self._load_geo_sources()
        self._populate_dropdowns()
        
        # --- Hubungkan Sinyal ---
        self.cmb_region.currentIndexChanged.connect(self._on_region_changed)
        self.btn_cut.clicked.connect(self.on_cut_clicked)
        # Tambahkan koneksi untuk tombol Reset jika diperlukan
        # self.btn_reset.clicked.connect(self.on_reset_clicked)

    def set_current_user(self, user: dict | None):
        self.current_user = user or {}

    def _init_ui(self):
        self.setObjectName("SellerSimulationRoot")
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setObjectName("SimScroll")
        root.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        v = QVBoxLayout(container)
        v.setContentsMargins(4, 4, 4, 24)
        v.setSpacing(16)

        map_box = QFrame()
        map_box.setObjectName("MapBox")
        map_box.setMinimumHeight(450) # Perbesar sedikit area peta
        map_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding) # Buat lebih fleksibel
        map_layout = QVBoxLayout(map_box)
        map_layout.setContentsMargins(8, 8, 8, 8) # Perkecil margin internal
        title = QLabel("Area Peta Interaktif")
        title.setObjectName("MapTitle")
        map_layout.addWidget(title)
        map_layout.addWidget(self.web_view)
        v.addWidget(map_box)

        input_box = QFrame()
        input_box.setObjectName("InputBox")
        input_layout = QVBoxLayout(input_box)
        input_layout.setContentsMargins(16, 16, 16, 16)
        input_layout.setSpacing(12)

        # ... (Sisa layout UI Anda tetap sama persis)
        row_mode = QHBoxLayout(); lbl_mode = QLabel("Mode"); lbl_mode.setObjectName("FieldLabel"); self.cmb_mode = QComboBox(); self.cmb_mode.setObjectName("Combo"); self.cmb_mode.addItems(["Node", "Edge"]); row_mode.addWidget(lbl_mode); row_mode.addWidget(self.cmb_mode); input_layout.addLayout(row_mode)
        row_region = QHBoxLayout(); lbl_region = QLabel("Daerah"); lbl_region.setObjectName("FieldLabel"); self.cmb_region = QComboBox(); self.cmb_region.setObjectName("Combo"); row_region.addWidget(lbl_region); row_region.addWidget(self.cmb_region); input_layout.addLayout(row_region)
        row_street = QHBoxLayout(); lbl_street = QLabel("Nama Jalan"); lbl_street.setObjectName("FieldLabel"); self.cmb_street = QComboBox(); self.cmb_street.setObjectName("Combo"); self.cmb_street.setEditable(False); self.cmb_street.setMinimumWidth(320); row_street.addWidget(lbl_street); row_street.addWidget(self.cmb_street, 1); input_layout.addLayout(row_street)
        btn_row = QHBoxLayout(); btn_row.addStretch(1); self.btn_cut = QPushButton("Cut"); self.btn_cut.setObjectName("Primary"); self.btn_reset = QPushButton("Reset"); self.btn_reset.setObjectName("Secondary"); btn_row.addWidget(self.btn_cut); btn_row.addWidget(self.btn_reset); input_layout.addLayout(btn_row)
        v.addWidget(input_box)
        v.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Salin stylesheet lengkap Anda ke sini
        self.setStyleSheet("""
            #SellerSimulationRoot { background: transparent; } #SimScroll { border: none; background: transparent; } #MapBox { background: #F8FBFD; border: 2px dashed #C8E6F0; border-radius: 12px; } #MapTitle { font-size: 16px; font-weight: 700; color: #0f5b6b; } #InputBox { background: #F9FCFF; border: 1px solid #E1F0F5; border-radius: 12px; } #FieldLabel { min-width: 110px; font-size: 12px; color: #2C5F6F; font-weight: 600; } #Combo { padding: 6px 10px; border: 1px solid #CFE6EE; border-radius: 8px; background: white; color: #0B3D91; } QPushButton#Primary { background-color: #D32F2F; color: white; padding: 8px 18px; border: none; border-radius: 8px; font-weight: bold; } QPushButton#Primary:hover { background-color: #E53935; } QPushButton#Primary:pressed { background-color: #C62828; } QPushButton#Secondary { background-color: #ECEFF1; color: #37474F; padding: 8px 18px; border: none; border-radius: 8px; font-weight: bold; } QPushButton#Secondary:hover { background-color: #E0E0E0; } QPushButton#Secondary:pressed { background-color: #CFD8DC; }
        """)

    def load_map_if_needed(self):
        if self.map_loaded: return
        print("--- LAZY LOADING MAP SEKARANG ---")
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        filename = os.path.join(project_root, "logic", "graph", "road_map_detailed.html")
        
        if os.path.exists(filename):
            settings = self.web_view.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            self.web_view.load(QUrl.fromLocalFile(filename))
            self.map_loaded = True
        else:
            print(f"ERROR: File peta tidak ditemukan di {filename}")
            self.web_view.setHtml("<h3>File peta tidak ditemukan.</h3>")

    def on_load_finished(self, ok):
        print(f"Halaman simulasi selesai dimuat (Success: {ok})")

    def _load_geo_sources(self):
        self._all_features_data = []
        self.region_to_streets = {}
        self.regions = []
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            area_path = os.path.join(project_root, "logic", "graph", "intersections_area.geojson")
            if os.path.exists(area_path):
                with open(area_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Simpan data lengkap untuk pencarian nanti
                self._all_features_data = data.get("features", [])
                self._map_region_to_streets()
        except Exception as e:
            print(f"Error memuat atau parsing GeoJSON: {e}")

    def _map_region_to_streets(self):
        region_to_streets = {}
        for feature in self._all_features_data:
            props = feature.get("properties", {})
            # Gunakan "Daerah Tidak Dikenal" sebagai fallback
            region = (props.get("region_name") or "Daerah Tidak Dikenal").strip()
            inter = props.get("intersection_name", "")
            if inter: # Hanya proses jika ada nama persimpangan
                # Pisahkan nama jalan jika ada simbol '&'
                parts = [p.strip() for p in inter.split("&") if p.strip()]
                for p in parts:
                    region_to_streets.setdefault(region, set()).add(p)
        self.region_to_streets = {k: sorted(list(v)) for k, v in region_to_streets.items()}
        self.regions = sorted(self.region_to_streets.keys())

    def _populate_dropdowns(self):
        try:
            self.cmb_region.clear()
            if self.regions:
                self.cmb_region.addItems(self.regions)
                if self.cmb_region.count() > 0:
                    self._on_region_changed(0)
        except Exception as e:
            print(f"Error mengisi dropdown daerah: {e}")

    def _on_region_changed(self, index):
        try:
            region = self.cmb_region.currentText()
            streets = self.region_to_streets.get(region, [])
            self.cmb_street.blockSignals(True)
            self.cmb_street.clear()
            if streets:
                self.cmb_street.addItems(streets)
            self.cmb_street.blockSignals(False)
        except Exception as e:
            print(f"Error mengubah jalan: {e}")
            
    # --- FUNGSI UTAMA UNTUK TOMBOL CUT ---
    def on_cut_clicked(self):
        """Dipanggil saat tombol 'Cut' diklik."""
        
        # 1. Dapatkan nama jalan yang dipilih dari dropdown
        # Kita gunakan `currentText()` karena ComboBox kita tidak editable.
        selected_intersection_name = self.cmb_street.currentText()
        if not selected_intersection_name:
            print("Tidak ada nama jalan/persimpangan yang dipilih.")
            return

        # Hanya proses jika mode 'Node' yang dipilih
        if self.cmb_mode.currentText() != "Node":
            print(f"Mode '{self.cmb_mode.currentText()}' tidak didukung untuk operasi Cut.")
            return

        print(f"Tombol Cut diklik untuk node: '{selected_intersection_name}'")

        # 2. Cari data lengkap (termasuk koordinat) dari data GeoJSON yang sudah dimuat
        target_coords = None
        for feature in self._all_features_data:
            props = feature.get("properties", {})
            # Cari nama persimpangan yang mengandung nama jalan yang dipilih
            # Ini lebih fleksibel daripada pencocokan persis
            if selected_intersection_name in props.get("intersection_name", ""):
                geometry = feature.get("geometry", {})
                if geometry.get("type") == "Point":
                    # Koordinat di GeoJSON: [longitude, latitude]
                    coords = geometry.get("coordinates")
                    if coords and len(coords) == 2:
                        # Kita butuh format [latitude, longitude] untuk Leaflet
                        target_coords = [coords[1], coords[0]] 
                        print(f"Koordinat ditemukan: {target_coords}")
                        break
        
        if not target_coords:
            print(f"Koordinat untuk '{selected_intersection_name}' tidak ditemukan di GeoJSON.")
            return

        # 3. Buat string JavaScript untuk dieksekusi di web view
        lat, lon = target_coords
        # Kita akan memanggil fungsi JS `removeMarkerByCoords` dengan koordinat
        js_command = f"removeMarkerByCoords({lat}, {lon});"
        
        print(f"Mengirim perintah ke JavaScript: {js_command}")
        
        # 4. Jalankan perintah JavaScript di halaman web
        self.web_view.page().runJavaScript(js_command)