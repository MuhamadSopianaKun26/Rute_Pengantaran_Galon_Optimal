"""
UI_sl_simulation.py
Halaman Simulasi (PyQt6) – menampilkan layout dengan QScrollArea vertikal,
area map placeholder di bagian atas, input dropdown (Mode, Daerah, Nama Jalan),
serta tombol Cut dan Reset. Hanya tampilan/stylesheet, tanpa logika.
"""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QComboBox, QPushButton, QSizePolicy, QSpacerItem
)
import os
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtCore import QUrl
from PyQt6.QtWebChannel import QWebChannel
import json


class SellerSimulation(QWidget):
    def __init__(self, parent=None, current_user: dict | None = None):
        super().__init__(parent)
        self.current_user = current_user or {}

        # Web view disiapkan, tapi tidak langsung memuat file.
        self.map_loaded = False
        self.web_view = QWebEngineView()
        self.channel = QWebChannel()
        self.web_view.page().setWebChannel(self.channel)
        self.web_view.loadFinished.connect(self.on_load_finished)
        # Izinkan akses file/local dan remote resource
        self.web_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        self.web_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )

        self._init_ui()
        self._load_geo_sources()
        self._populate_regions()
        try:
            self.cmb_region.currentIndexChanged.connect(self._on_region_changed)
        except Exception:
            pass

    def set_current_user(self, user: dict | None):
        self.current_user = user or {}

    def _init_ui(self):
        self.setObjectName("SellerSimulationRoot")
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Scroll area vertikal
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setObjectName("SimScroll")
        root.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        v = QVBoxLayout(container)
        v.setContentsMargins(4, 4, 4, 24)
        v.setSpacing(16)

        # Area Map Placeholder (akan diisi canvas peta nanti)
        map_box = QFrame()
        map_box.setObjectName("MapBox")
        map_box.setMinimumHeight(360)
        map_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        map_layout = QVBoxLayout(map_box)
        map_layout.setContentsMargins(16, 16, 16, 16)
        map_layout.setSpacing(8)
        title = QLabel("Area Peta")
        title.setObjectName("MapTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        map_layout.addWidget(title)
        map_layout.addWidget(self.web_view)
        v.addWidget(map_box)

        # Input Section
        input_box = QFrame()
        input_box.setObjectName("InputBox")
        input_layout = QVBoxLayout(input_box)
        input_layout.setContentsMargins(16, 16, 16, 16)
        input_layout.setSpacing(12)

        # Row 1: Mode (Edge/Node)
        row_mode = QHBoxLayout()
        lbl_mode = QLabel("Mode")
        lbl_mode.setObjectName("FieldLabel")
        self.cmb_mode = QComboBox()
        self.cmb_mode.setObjectName("Combo")
        self.cmb_mode.addItems(["Edge", "Node"]) 
        row_mode.addWidget(lbl_mode)
        row_mode.addWidget(self.cmb_mode)
        input_layout.addLayout(row_mode)

        # Row 2: Daerah
        row_region = QHBoxLayout()
        lbl_region = QLabel("Daerah")
        lbl_region.setObjectName("FieldLabel")
        self.cmb_region = QComboBox()
        self.cmb_region.setObjectName("Combo")
        # items diisi dinamis dari geojson
        row_region.addWidget(lbl_region)
        row_region.addWidget(self.cmb_region)
        input_layout.addLayout(row_region)

        # Row 3: Nama Jalan
        row_street = QHBoxLayout()
        lbl_street = QLabel("Nama Jalan")
        lbl_street.setObjectName("FieldLabel")
        self.cmb_street = QComboBox()
        self.cmb_street.setObjectName("Combo")
        self.cmb_street.setEditable(False)
        self.cmb_street.setMinimumWidth(320)
        # Placeholder isi contoh
        self.cmb_street.addItems([
            "Jalan Sariasih", "Jalan Sarimanah 2", "Jalan Sarijadi Raya", "Jalan Setrasari"
        ])
        row_street.addWidget(lbl_street)
        row_street.addWidget(self.cmb_street, 1)
        input_layout.addLayout(row_street)

        # Action buttons (Cut / Reset)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_cut = QPushButton("Cut")
        self.btn_cut.setObjectName("Primary")
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setObjectName("Secondary")
        btn_row.addWidget(self.btn_cut)
        btn_row.addWidget(self.btn_reset)
        input_layout.addLayout(btn_row)

        v.addWidget(input_box)

        # Spacer akhir agar scroll nyaman
        v.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Stylesheet
        self.setStyleSheet(
            """
            #SellerSimulationRoot {
                background: transparent;
            }
            #SimScroll {
                border: none;
                background: transparent;
            }
            #MapBox {
                background: #F8FBFD;
                border: 2px dashed #C8E6F0;
                border-radius: 12px;
            }
            #MapTitle {
                font-size: 16px;
                font-weight: 700;
                color: #0f5b6b;
            }
            
            #InputBox {
                background: #F9FCFF;
                border: 1px solid #E1F0F5;
                border-radius: 12px;
            }
            #FieldLabel {
                min-width: 110px;
                font-size: 12px;
                color: #2C5F6F;
                font-weight: 600;
            }
            #Combo {
                padding: 6px 10px;
                border: 1px solid #CFE6EE;
                border-radius: 8px;
                background: white;
                color: #0B3D91;
            }
            QPushButton#Primary {
                background-color: #2E7D32;
                color: white;
                padding: 8px 18px;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton#Primary:hover { background-color: #388E3C; }
            QPushButton#Primary:pressed { background-color: #1B5E20; }

            QPushButton#Secondary {
                background-color: #ECEFF1;
                color: #37474F;
                padding: 8px 18px;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton#Secondary:hover { background-color: #E0E0E0; }
            QPushButton#Secondary:pressed { background-color: #CFD8DC; }
            """
        )



    def on_load_finished(self):
        print("Halaman sudah dimuat dan siap")
    
    def load_map_if_needed(self):
        """
        Fungsi ini akan dipanggil oleh main window TEPAT SEBELUM
        halaman ini ditampilkan.
        """
        # Jika sudah dimuat, jangan lakukan apa-apa
        if self.map_loaded:
            return

        print("--- LAZY LOADING MAP SEKARANG ---")

        # Resolve path HTML secara robust berbasis lokasi file ini
        # .../Matematika_Diskrit/UI/seller/UI_sl_simulation.py -> project root = 3x dirname
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        filename = os.path.join(project_root, "logic", "graph", "road_map_detailed.html")
        print(f"Mencoba memuat: {filename}")
        print(f"File ada: {os.path.exists(filename)}")

        # Terapkan pengaturan keamanan
        settings = self.web_view.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )

        # Muat hanya jika file ada, jika tidak tampilkan pesan di area peta
        if os.path.exists(filename):
            self.web_view.load(QUrl.fromLocalFile(filename))
        else:
            try:
                # Tampilkan pesan fallback di map_box
                self.web_view.setHtml("""
                    <html><body style='font-family:Segoe UI;color:#2C5F6F;padding:16px;'>
                    <h3>File peta tidak ditemukan</h3>
                    <p>Pastikan file <code>logic/graph/road_map_detailed.html</code> tersedia.</p>
                    </body></html>
                """)
            except Exception:
                pass
        
        # Set flag
        self.map_loaded = True

    def _load_geo_sources(self):
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            area_path = os.path.join(project_root, "logic", "graph", "intersections_area.geojson")
            self._features = []
            if os.path.exists(area_path):
                with open(area_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                feats = data.get("features", [])
                for ft in feats:
                    props = ft.get("properties", {})
                    name = props.get("intersection_name")
                    region = props.get("region_name")
                    if isinstance(name, str) and isinstance(region, str):
                        self._features.append({"intersection_name": name, "region_name": region})
            self._map_region_to_streets()
        except Exception:
            self._features = []
            self.region_to_streets = {}
            self.regions = []

    def _map_region_to_streets(self):
        region_to_streets = {}
        for item in self._features:
            region = item["region_name"].strip()
            inter = item["intersection_name"]
            parts = [p.strip() for p in inter.split("&") if p.strip()]
            for p in parts:
                region_to_streets.setdefault(region, set()).add(p)
        self.region_to_streets = {k: sorted(v) for k, v in region_to_streets.items()}
        self.regions = sorted(self.region_to_streets.keys())

    def _populate_regions(self):
        try:
            self.cmb_region.clear()
            if getattr(self, "regions", None):
                self.cmb_region.addItems(self.regions)
                self._on_region_changed(0)
        except Exception:
            pass

    def _on_region_changed(self, idx):
        try:
            region = self.cmb_region.currentText()
            streets = self.region_to_streets.get(region, [])
            self.cmb_street.blockSignals(True)
            self.cmb_street.clear()
            if streets:
                self.cmb_street.addItems(streets)
            self.cmb_street.blockSignals(False)
        except Exception:
            pass
