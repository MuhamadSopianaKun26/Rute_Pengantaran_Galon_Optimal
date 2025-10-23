"""
UI_sl_simulation.py
Halaman Simulasi (PyQt6) – menampilkan peta dan kontrol untuk memanipulasi node/edge.
Menggunakan pendekatan baru: Python hanya mengirim koordinat node.
"""

import os
import json
from PyQt6.QtCore import Qt, QUrl, pyqtSlot, QObject
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QComboBox, QPushButton, QSizePolicy, QSpacerItem, QLineEdit, QMessageBox
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel

class SellerSimulation(QWidget):
    def __init__(self, parent=None, current_user: dict | None = None, marker_deleted=None, desc_marker=None):
        super().__init__(parent)
        self.current_user = current_user or {}
        self.map_loaded = False
        self.desc_marker = desc_marker

        self.marker_deleted = marker_deleted

        # --- Data Stores ---
        self._all_nodes_data = [] # Dari intersections_area.geojson
        # self._all_roads_data TIDAK DIPERLUKAN LAGI
        self.region_to_nodes_map = {} 
        self.regions = []

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
        self.btn_reset.clicked.connect(self.on_reset_clicked)

    def set_current_user(self, user: dict | None):
        self.current_user = user or {}

    def _init_ui(self):
        # (Kode _init_ui Anda dari prompt sebelumnya sudah benar)
        self.setObjectName("SellerSimulationRoot")
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16); root.setSpacing(12)
        scroll = QScrollArea(self); scroll.setWidgetResizable(True); scroll.setObjectName("SimScroll"); root.addWidget(scroll)
        container = QWidget(); scroll.setWidget(container)
        v = QVBoxLayout(container); v.setContentsMargins(4, 4, 4, 24); v.setSpacing(16)
        map_box = QFrame(); map_box.setObjectName("MapBox"); map_box.setMinimumHeight(450); map_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        map_layout = QVBoxLayout(map_box); map_layout.setContentsMargins(8, 8, 8, 8)
        title = QLabel("Area Peta Interaktif"); title.setObjectName("MapTitle"); map_layout.addWidget(title)
        map_layout.addWidget(self.web_view); v.addWidget(map_box)
        input_box = QFrame(); input_box.setObjectName("InputBox")
        input_layout = QVBoxLayout(input_box); input_layout.setContentsMargins(16, 16, 16, 16); input_layout.setSpacing(12)
        row_mode = QHBoxLayout(); lbl_mode = QLabel("Mode"); lbl_mode.setObjectName("FieldLabel"); self.cmb_mode = QComboBox(); self.cmb_mode.setObjectName("Combo"); self.cmb_mode.addItems(["Node", "Edge"]); row_mode.addWidget(lbl_mode); row_mode.addWidget(self.cmb_mode); input_layout.addLayout(row_mode)
        row_region = QHBoxLayout(); lbl_region = QLabel("Daerah"); lbl_region.setObjectName("FieldLabel"); self.cmb_region = QComboBox(); self.cmb_region.setObjectName("Combo"); row_region.addWidget(lbl_region); row_region.addWidget(self.cmb_region); input_layout.addLayout(row_region)
        row_street = QHBoxLayout(); lbl_street = QLabel("Nama Node"); lbl_street.setObjectName("FieldLabel"); self.cmb_street = QComboBox(); self.cmb_street.setObjectName("Combo"); self.cmb_street.setEditable(False); self.cmb_street.setMinimumWidth(320); row_street.addWidget(lbl_street); row_street.addWidget(self.cmb_street, 1); input_layout.addLayout(row_street)
        row_desc = QHBoxLayout(); lbl_desc = QLabel("Deskripsi"); lbl_desc.setObjectName("FieldLabel"); self.input_desc = QLineEdit(); self.input_desc.setObjectName("Combo"); self.input_desc.setMinimumWidth(320); row_desc.addWidget(lbl_desc); row_desc.addWidget(self.input_desc, 1); input_layout.addLayout(row_desc)
        btn_row = QHBoxLayout(); btn_row.addStretch(1); self.btn_cut = QPushButton("Cut"); self.btn_cut.setObjectName("Primary"); self.btn_reset = QPushButton("Reset"); self.btn_reset.setObjectName("Secondary"); btn_row.addWidget(self.btn_cut); btn_row.addWidget(self.btn_reset); input_layout.addLayout(btn_row)
        v.addWidget(input_box)
        v.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        self.setStyleSheet("""
            #SellerSimulationRoot { background: transparent; } #SimScroll { border: none; background: transparent; } #MapBox { background: #F8FBFD; border: 2px dashed #C8E6F0; border-radius: 12px; } #MapTitle { font-size: 16px; font-weight: 700; color: #0f5b6b; } #InputBox { background: #F9FCFF; border: 1px solid #E1F0F5; border-radius: 12px; } #FieldLabel { min-width: 110px; font-size: 12px; color: #2C5F6F; font-weight: 600; } #Combo { padding: 6px 10px; border: 1px solid #CFE6EE; border-radius: 8px; background: white; color: #0B3D91; } 
            QPushButton#Primary { background-color: #D32F2F; color: white; padding: 8px 18px; border: none; border-radius: 8px; font-weight: bold; } 
            QPushButton#Primary:hover { background-color: #E53935; } 
            QPushButton#Primary:pressed { background-color: #C62828; } 
            QPushButton#Secondary { background-color: #ECEFF1; color: #37474F; padding: 8px 18px; border: none; border-radius: 8px; font-weight: bold; } 
            QPushButton#Secondary:hover { background-color: #E0E0E0; } 
            QPushButton#Secondary:pressed { background-color: #CFD8DC; }
        """)

    def get_project_root(self):
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def load_map_if_needed(self):
        if self.map_loaded: return
        print("--- LAZY LOADING MAP SEKARANG ---")
        filename = os.path.join(self.get_project_root(), "logic", "graph", "road_map_detailed.html")
        
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

    # --- FUNGSI YANG DIPERBARUI ---
    def _load_geo_sources(self):
        """HANYA memuat data Node (Intersections)."""
        project_root = self.get_project_root()
        
        try:
            area_path = os.path.join(project_root, "logic", "graph", "output.geojson")
            if os.path.exists(area_path):
                with open(area_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._all_nodes_data = data.get("features", [])
            else:
                 print(f"File node tidak ditemukan: {area_path}")
                 self._all_nodes_data = []
            print(f"Loaded {len(self._all_nodes_data)} nodes from intersections_area.geojson")
        except Exception as e:
            print(f"Error memuat intersections_area.geojson: {e}")
            self._all_nodes_data = []
            
        # Hapus bagian yang memuat roads_names.geojson
        
        self._map_region_to_streets()

    def _map_region_to_streets(self):
        # (Fungsi ini sudah benar dari sebelumnya, tidak perlu diubah)
        region_to_nodes = {}
        for feature in self._all_nodes_data:
            props = feature.get("properties", {})
            region = (props.get("region_name") or "Daerah Tidak Dikenal").strip()
            node_name = props.get("intersection_name", "") 
            if node_name:
                region_to_nodes.setdefault(region, set()).add(node_name)
        self.region_to_nodes_map = {k: sorted(list(v)) for k, v in region_to_nodes.items()}
        self.regions = sorted(self.region_to_nodes_map.keys())

    def _populate_dropdowns(self):
        # (Fungsi ini sudah benar dari sebelumnya, tidak perlu diubah)
        try:
            self.cmb_region.clear()
            if self.regions:
                self.cmb_region.addItems(self.regions)
                if self.cmb_region.count() > 0:
                    self.cmb_region.setCurrentIndex(0)
                    self._on_region_changed(0) 
            else:
                self._on_region_changed(-1) 
        except Exception as e:
            print(f"Error mengisi dropdown daerah: {e}")

    def _on_region_changed(self, index):
        # (Fungsi ini sudah benar dari sebelumnya, tidak perlu diubah)
        try:
            self.cmb_street.blockSignals(True)
            self.cmb_street.clear()
            if index < 0:
                self.cmb_street.blockSignals(False); return
            region = self.cmb_region.currentText()
            nodes_in_region = self.region_to_nodes_map.get(region, [])
            if nodes_in_region: self.cmb_street.addItems(nodes_in_region)
            self.cmb_street.blockSignals(False)
        except Exception as e:
            print(f"Error mengubah nama node: {e}")
            
    # --- FUNGSI on_cut_clicked YANG DIPERBARUI & JAUH LEBIH SEDERHANA ---
    def on_cut_clicked(self):
        """
        Dipanggil saat tombol 'Cut' diklik.
        Hanya mencari koordinat node dan mengirimkannya ke JS.
        """
        text = self.input_desc.text()
        if not text:
            return QMessageBox.warning(self, "Peringatan", "Deskripsi tidak boleh kosong!")
        
        if not self.desc_marker:
            self.desc_marker.append(text)
        else:
            self.desc_marker[0] = text
            
        print(self.desc_marker)
        mode = self.cmb_mode.currentText()
        if mode != "Node":
            print(f"Mode '{mode}' belum didukung untuk operasi Cut.")
            return

        selected_node_name = self.cmb_street.currentText()
        if not selected_node_name:
            print("Tidak ada node yang dipilih.")
            return
        self.marker_deleted.append(selected_node_name)

        print(f"Tombol Cut diklik untuk node: '{selected_node_name}'")

        # 1. Cari node di data intersection kita
        target_node_feature = None
        for feature in self._all_nodes_data:
            if feature.get("properties", {}).get("intersection_name") == selected_node_name:
                target_node_feature = feature
                break
        
        if not target_node_feature:
            print(f"Node '{selected_node_name}' tidak ditemukan di _all_nodes_data.")
            return

        # 2. Dapatkan Koordinat
        node_geom = target_node_feature.get("geometry", {})
        node_coords_lonlat = node_geom.get("coordinates") # Format GeoJSON [lon, lat]
        
        if not node_coords_lonlat:
            print("Node tidak memiliki koordinat.")
            return
            
        # Konversi ke [lat, lon] untuk menghapus marker di Leaflet
        node_coords_latlon_for_marker = [node_coords_lonlat[1], node_coords_lonlat[0]]

        # 3. Hapus logika pencarian edge. Kita tidak membutuhkannya lagi.

        # 4. Siapkan payload HANYA dengan koordinat.
        # Kita kirim kedua format (lon/lat dan lat/lon) agar JS mudah
        payload = {
            "marker_coords": node_coords_latlon_for_marker, # [lat, lon] untuk marker
            "node_coords": node_coords_lonlat             # [lon, lat] untuk edge
        }
        
        js_payload = json.dumps(payload)
        
        # 5. Buat dan jalankan perintah JavaScript baru
        # Kita ganti nama fungsinya agar lebih jelas
        js_command = f"cutLayersByCoord({js_payload});"
        
        print(f"Mengirim perintah ke JavaScript: {js_command}")
        self.web_view.page().runJavaScript(js_command)

    def on_reset_clicked(self):
        """Memuat ulang peta ke kondisi aslinya."""
        print("Tombol Reset diklik. Memuat ulang peta...")
        self.map_loaded = False 
        self.load_map_if_needed()
