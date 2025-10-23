from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame,
    QListWidget, QListWidgetItem, QPushButton, QSpacerItem, QSizePolicy, QMessageBox, QScrollArea
)
import textwrap
import os, json, datetime, random
from datetime import time
import math
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import geopandas as gpd
import osmnx as ox
from logic.graph.path_finder import muat_data_peta_dan_lokasi, cari_rute_by_nama


def _db_path(filename: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, 'Database', filename)


def _load_products_price_map() -> dict:
    path = _db_path('products.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f) or {}
        products = data.get('products') or []
        return {p.get('name', ''): int(p.get('price', 0) or 0) for p in products if p.get('name')}
    except Exception:
        return {}


def _fmt_hhmm(dt: datetime.datetime) -> str:
    try:
        return dt.strftime("%H:%M")
    except Exception:
        return "-"


class DeliveryPreviewDialog(QDialog):
    """
    Dialog Preview Pengiriman (Seller)

    - Bagian atas: placeholder peta rute (5 bagian)
    - Bagian bawah (3 bagian):
      - Kiri: Nama & akun pembeli, alamat, estimasi waktu pengiriman, estimasi sampai (HH:mm)
      - Kanan: Rincian pesanan (nama item, qty, harga) + total harga
    - Bawah: Tombol Kembali dan Kirim Sekarang
    """

    def __init__(self, order: dict, parent=None, marker_deleted=None, desc_marker=None):
        super().__init__(parent)
        self.order = order or {}
        self._price_map = _load_products_price_map()
        self.marker_deleted=marker_deleted
        self.desc_marker=desc_marker

        self.setWindowTitle("Preview Pengiriman")
        self.resize(1000, 720)
        self.setModal(True)

        # Tema biru aqua sejalan dengan main.py
        # Menggunakan warna: judul #2C5F6F, aksen #5A8A9B
        self.setStyleSheet(
            """
            QDialog { background: #F8F9FA; }
            QLabel#Title { font-size: 20px; font-weight: 800; color: #2C5F6F; }
            QLabel#SectionTitle { font-size: 14px; font-weight: 700; color: #2C5F6F; }
            QFrame#MapBox { background: white; border: 2px dashed #5A8A9B; border-radius: 12px; }
            QFrame#InfoBox { background: white; border: 1px solid rgba(0,0,0,0.06); border-radius: 12px; }
            QListWidget { border: none; }
            QPushButton#Primary { background: #2196F3; color: white; font-weight: 700; padding: 10px 18px; border-radius: 8px; }
            QPushButton#Primary:hover { background: #1E88E5; }
            QPushButton#Secondary { background: white; color: #2C5F6F; font-weight: 600; padding: 10px 18px; border: 1px solid #5A8A9B; border-radius: 8px; }
            QPushButton#Secondary:hover { background: #E3F2FD; }
            """
        )

        self._build_ui()
        self._populate_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Preview Pengiriman")
        title.setObjectName("Title")
        layout.addWidget(title)

        # Bagian atas: Analisis Rute Pengantaran 
        self.map_box = QFrame()
        self.map_box.setObjectName("MapBox")
        map_layout = QVBoxLayout(self.map_box)
        map_layout.setContentsMargins(16, 16, 16, 16)
        map_layout.setSpacing(10) # Sedikit perbesar jarak antar label

        map_title = QLabel("Analisis Rute Pengantaran")
        map_title.setObjectName("SectionTitle")
        self.map_desc = QLabel("Visualisasi rute akan ditampilkan di jendela terpisah saat Anda menekan tombol di bawah.")
        self.map_desc.setStyleSheet("color:#5A8A9B;")
        self.map_desc.setWordWrap(True)
        map_layout.addWidget(map_title)
        map_layout.addWidget(self.map_desc)
        # Label hasil perhitungan rute
        self.lbl_distance = QLabel("Jarak tempuh: -")
        self.lbl_timecalc = QLabel("Estimasi waktu (100 m/s): -")
        self.lbl_distance.setStyleSheet("color:#2C5F6F;font-weight:600;")
        self.lbl_timecalc.setStyleSheet("color:#2C5F6F;")
        map_layout.addWidget(self.lbl_distance)

        # Label untuk menampilkan Estimasi Waktu (berdasarkan 36 km/jam)
        self.lbl_estimated_time = QLabel("Estimasi Waktu Tempuh: Menghitung...")
        self.lbl_estimated_time.setStyleSheet("color:#3b6a75; font-size: 13px;")
        map_layout.addWidget(self.lbl_estimated_time)
        
        # Label untuk narasi/analisis tambahan
        self.lbl_analysis_text = QLabel("Analisis:\nMenunggu perhitungan rute...")
        self.lbl_analysis_text.setStyleSheet("color:#5A8A9B; font-style: italic;")
        self.lbl_analysis_text.setWordWrap(True)
        map_layout.addWidget(self.lbl_analysis_text)

        # Spacer agar konten tidak terlalu renggang jika rute pendek
        map_layout.addStretch(1)

        # Bagian bawah: Info kiri + Rincian kanan (3 bagian tinggi)
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        # Kiri: Info pembeli & estimasi
        self.info_box = QFrame()
        self.info_box.setObjectName("InfoBox")
        info_layout = QVBoxLayout(self.info_box)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(8)

        self.lbl_buyer = QLabel()
        self.lbl_buyer.setObjectName("SectionTitle")

        self.lbl_address = QLabel()
        self.lbl_address.setWordWrap(True)
        self.lbl_address.setStyleSheet("color:#3b6a75;")

        self.lbl_order_type = QLabel()
        self.lbl_order_type.setStyleSheet("color:#2C5F6F; font-weight:bold;")
        self.lbl_eta_duration = QLabel()
        self.lbl_eta_duration.setStyleSheet("color:#2C5F6F;")
        self.lbl_eta_arrival = QLabel()
        self.lbl_eta_arrival.setStyleSheet("color:#2C5F6F;")

        info_layout.addWidget(self.lbl_buyer)
        info_layout.addWidget(self.lbl_address)
        info_layout.addSpacing(8)
        info_layout.addWidget(self.lbl_order_type)
        info_layout.addWidget(self.lbl_eta_duration)
        info_layout.addWidget(self.lbl_eta_arrival)
        info_layout.addStretch(1)

        # Kanan: Rincian pesanan
        self.detail_box = QFrame()
        self.detail_box.setObjectName("InfoBox")
        detail_layout = QVBoxLayout(self.detail_box)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(8)

        detail_title = QLabel("Rincian Pesanan")
        detail_title.setObjectName("SectionTitle")
        self.list_items = QListWidget()
        self.lbl_total = QLabel()
        self.lbl_total.setStyleSheet("font-weight:800;color:#2C5F6F;font-size:14px;")

        detail_layout.addWidget(detail_title)
        detail_layout.addWidget(self.list_items)
        detail_layout.addWidget(self.lbl_total)

        bottom.addWidget(self.info_box, 2)
        bottom.addWidget(self.detail_box, 1)

        # Tombol aksi
        btn_row = QHBoxLayout()
        # Tombol fitur kiri: Rute Tercepat, Node
        self.btn_fastest = QPushButton("Rute Tercepat")
        self.btn_fastest.setObjectName("Secondary")
        self.btn_nodes = QPushButton("Node")
        self.btn_nodes.setObjectName("Secondary")
        self.btn_back = QPushButton("Kembali")
        self.btn_back.setObjectName("Secondary")
        self.btn_send = QPushButton("Kirim Sekarang")
        self.btn_send.setObjectName("Primary")
        # Urutan kiri -> kanan sesuai permintaan
        btn_row.addWidget(self.btn_fastest)
        btn_row.addWidget(self.btn_nodes)
        btn_row.addSpacing(12)
        btn_row.addWidget(self.btn_back)
        btn_row.addWidget(self.btn_send)

        layout.addWidget(self.map_box, stretch=5)
        layout.addLayout(bottom, stretch=3)
        layout.addLayout(btn_row)

        # Events
        self.btn_back.clicked.connect(self.reject)
        self.btn_send.clicked.connect(self._on_send)
        self.btn_fastest.clicked.connect(self._on_show_fastest_route)
        self.btn_nodes.clicked.connect(self._on_show_nodes_timeline)

    def _populate_data(self):
        # Nama & akun pembeli
        name = self.order.get('customer_name') or '-'
        account = self.order.get('user_email') or self.order.get('user_name') or '-'
        self.lbl_buyer.setText(f"{name}  ( {account} )")

        # Alamat
        area = self.order.get('area') or '-'
        street = self.order.get('street') or '-'
        note = self.order.get('note')
        note_text = f"\nKeterangan: {note}" if note else ""
        self.lbl_address.setText(f"Alamat: {area} - {street}{note_text}")

        # Order Type
        order_type = self.order.get('schedule')
        self.lbl_order_type.setText(f"Jadwal Pesanan: {order_type}")

        # Estimasi
        self._load_graph_if_needed()
        start_name = "Depot Air Pusat"
        dest_name = self._get_destination_name()
        edges = []
        length_km = 0.0
        if self.G is not None and self.gdf_lokasi is not None and dest_name:
            try:
                edges, length_km = cari_rute_by_nama(self.G, self.gdf_lokasi, start_name, dest_name, show_preview=False)
            except Exception:
                edges, length_km = [], 0.0
        # Pastikan waktu_kirim berupa datetime
        schedule = self.order.get('schedule') or 'Segera'
        if schedule != 'Segera':
            s = str(schedule).replace('.', ':')
            try:
                today = datetime.datetime.now()
                hh, mm = s.split(':')
                waktu_kirim_dt = today.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            except Exception:
                waktu_kirim_dt = datetime.datetime.now()
        else:
            waktu_kirim_dt = datetime.datetime.now()
        jumlah_tikungan = len(edges) if edges else 0

        if not edges or not length_km:
            # Tidak ada jalur yang ditemukan
            self.waktu_tempuh_detik = None
            self.waktu_tempuh = None
            self.lbl_eta_duration.setText("Estimasi Waktu Pengiriman: Tidak ada jalur yang ditemukan")
            self.lbl_eta_arrival.setText("Estimasi Sampai: -")
        else:
            total_detik = self.hitung_simulasi_kecepatan(float(length_km), waktu_kirim_dt, jumlah_tikungan)
            self.waktu_tempuh_detik = int(round(total_detik))
            menit = self.waktu_tempuh_detik // 60
            detik = self.waktu_tempuh_detik % 60
            # Pertahankan kompatibilitas: variabel menit yang dipakai bagian lain
            self.waktu_tempuh = menit
            self.lbl_eta_duration.setText(f"Estimasi Waktu Pengiriman: {menit} menit {detik} detik")
            arrival_str = self._estimate_arrival_hhmm(self.waktu_tempuh)
            self.lbl_eta_arrival.setText(f"Estimasi Sampai: {arrival_str}")

        # Rincian item & total
        total = 0
        items = self.order.get('items') or []
        for it in items:
            nm = it.get('name', 'Produk')
            qty = int(it.get('qty', 1) or 1)
            price = int(self._price_map.get(nm, 0))
            line_total = price * qty
            total += line_total
            text = f"{nm} x{qty} - Rp{line_total:,}"
            self.list_items.addItem(QListWidgetItem(text))

        self.lbl_total.setText(f"Total Harga: Rp{total:,}")

    def _estimate_duration_minutes(self) -> int:
        # Placeholder estimasi: 15 menit dasar + 2 menit per item
        try:
            count = sum(int(it.get('qty', 1) or 1) for it in (self.order.get('items') or []))
        except Exception:
            count = 1
        return max(10, 15 + 2 * count)

    def _estimate_arrival_hhmm(self, duration_min: int) -> str:
        # Jika terjadwal, gunakan jam terjadwal sebagai start, selain itu gunakan sekarang
        schedule = self.order.get('schedule') or 'Segera'
        start = datetime.datetime.now()
        if schedule and schedule != 'Segera':
            # format wishlist: "HH.mm" atau "HH:MM" -> normalisasi
            s = str(schedule).replace('.', ':')
            try:
                today = datetime.datetime.now()
                hh, mm = s.split(':')
                start = today.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            except Exception:
                pass
        arrival = start + datetime.timedelta(minutes=duration_min)
        return _fmt_hhmm(arrival)

    def _on_send(self):
        # Tidak mengubah status di sini — biarkan pemanggil yang memutuskan.
        self.accept()

    # ------------------------------
    # Integrasi LOGIC GRAPH
    # ------------------------------
    def _get_project_root(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    def _geojson_path(self) -> str:
        # Menggunakan intersections_area.geojson sesuai perubahan terbaru
        return os.path.join(self._get_project_root(), 'logic', 'graph', 'intersections_area.geojson')

    def _load_graph_if_needed(self):
        if hasattr(self, 'G') and hasattr(self, 'gdf_lokasi') and self.G is not None and self.gdf_lokasi is not None:
            return
        lokasi_peta = (-6.872, 107.578)  # pusat area
        path_geojson = os.path.abspath(self._geojson_path())
        try:
            exists = os.path.exists(path_geojson)
            print(f"[DEBUG] Memuat peta & GeoJSON... path_geojson={path_geojson} exists={exists}")
            if not exists:
                QMessageBox.warning(self, "GeoJSON Tidak Ditemukan", f"File tidak ditemukan:\n{path_geojson}")
                self.G, self.gdf_lokasi = None, None
                return
            G, gdf = muat_data_peta_dan_lokasi(lokasi_peta, path_ke_geojson=path_geojson)

            self.G_awal = G.copy()
            self.gdf_lokasi_awal = gdf.copy()

            osmid_to_remove = gdf[gdf["intersection_name"].isin(self.marker_deleted)]["osmid"].tolist()
            print("OSMID yang akan dihapus:", osmid_to_remove)

            gdf = gdf[~gdf["intersection_name"].isin(self.marker_deleted)]

            self.G, self.gdf_lokasi = G, gdf

            self.G.remove_nodes_from(osmid_to_remove)

            # Hapus node-node tersebut dari graph
            self.G.remove_nodes_from(osmid_to_remove)
            print("Nodes to remove:", osmid_to_remove)
            print("Node count sebelum hapus:", self.G.number_of_nodes())
            self.G.remove_nodes_from(osmid_to_remove)
            print("Node count setelah hapus:", self.G.number_of_nodes())

            print("Contoh node dan atribut di G:")
            for n, attr in list(self.G.nodes(data=True))[:10]:
                print(n, attr)


            
        except Exception as e:
            print(f"[ERROR] _load_graph_if_needed: {e}")
            print(f"[DEBUG] path_geojson={path_geojson}")
            self.G, self.gdf_lokasi = None, None

    def _get_destination_name(self) -> str:
        # Gunakan 'street' dari order sebagai nama tujuan (harus cocok dengan 'intersection_name' di GeoJSON)
        street = (self.order.get('street') or '').strip()
        if not street:
            return ''
        return street

    def _compute_route(self):
        self._load_graph_if_needed()
        if self.G is None or self.gdf_lokasi is None:
            QMessageBox.warning(self, "Gagal Memuat Peta", "Data peta atau GeoJSON tidak dapat dimuat.")
            # Reset label jika gagal
            self.lbl_distance.setText("Jarak Tempuh Total: Gagal memuat peta")
            self.lbl_estimated_time.setText("Estimasi Waktu Tempuh: Gagal memuat peta")
            self.lbl_analysis_text.setText("Analisis:\nTidak dapat menghitung rute karena data peta tidak tersedia.")
            return None, None, None
            
        start_name = "Depot Air Pusat" # Pastikan nama ini ADA di GeoJSON Anda
        dest_name = self._get_destination_name()
        if not dest_name:
            QMessageBox.information(self, "Tujuan Tidak Ditemukan", "Alamat tujuan (intersection_name) pembeli tidak tersedia atau tidak valid.")
            self.lbl_distance.setText("Jarak Tempuh Total: Tujuan tidak valid")
            self.lbl_estimated_time.setText("Estimasi Waktu Tempuh: Tujuan tidak valid")
            self.lbl_analysis_text.setText("Analisis:\nTidak dapat menghitung rute karena nama tujuan tidak ditemukan di data lokasi.")
            return None, None, None
        

        # --- HITUNG RUTE PADA GRAF SAAT INI (Normal atau Detour) ---
        current_edges, current_length_km = cari_rute_by_nama(self.G, self.gdf_lokasi, start_name, dest_name, show_preview=False)
        
        # --- HITUNG RUTE Lama PADA GRAF SAAT INI (Normal atau Detour) ---
        # current_edges_awal, current_length_km_awal = cari_rute_by_nama(self.G_awal, self.gdf_lokasi_awal, start_name, dest_name, show_preview=False)

        # Variabel untuk narasi akhir
        analysis_str = ""
        label_jarak = "Jarak Tempuh Total: "
        label_waktu = "Estimasi Waktu Tempuh: "

        # --- LOGIKA BARU: Cek apakah ada simulasi ---
        if self.marker_deleted:
            # Ada simulasi, coba hitung rute asli untuk perbandingan
            if self.G_awal:
                try:
                    # Muat GDF asli lagi untuk lookup nama lengkap
                    _, original_length_km = cari_rute_by_nama(self.G_awal, self.gdf_lokasi_awal, start_name, dest_name, show_preview=False)
                except Exception as e:
                    print(f"Gagal menghitung rute asli untuk perbandingan: {e}")
                    original_length_km = None
            else:
                original_length_km = None # Tidak bisa membandingkan jika G_original tidak ada

            if current_edges is None: # Rute alternatif TIDAK ditemukan
                reasons_str = self.desc_marker[0]
                analysis_str = (
                    f"Analisis:\n"
                    f"Rute normal dari '{start_name}' ke '{dest_name}' (jika ada) tidak dapat digunakan "
                    f"karena penutupan persimpangan {reasons_str}. "
                    f"Saat ini TIDAK ADA rute alternatif yang tersedia."
                )
                label_jarak = "Jarak Tempuh Total: Rute terputus!"
                label_waktu = "Estimasi Waktu Tempuh: Tidak dapat dihitung"
                current_length_km = None # Set agar tidak dihitung nanti

            elif original_length_km is not None: # Rute asli dan alternatif ditemukan
                kecepatan_km_per_menit = 36 / 60
                estimated_minutes_detour = current_length_km / kecepatan_km_per_menit
                
                reasons_str = self.desc_marker[0]
                analysis_str = (
                    f"Analisis:\n"
                    f"Rute terpendek normal adalah {original_length_km:.2f} km. "
                    f"Namun, dikarenakan adanya {reasons_str}, "
                    f"rute dialihkan menjadi {current_length_km:.2f} km (+{current_length_km - original_length_km:.2f} km). "
                    f"Dengan asumsi kecepatan 36 km/jam, estimasi waktu tempuh menjadi sekitar {math.ceil(estimated_minutes_detour)} menit."
                )
                label_jarak = f"Jarak Tempuh (Alternatif): {current_length_km:.2f} km"
                label_waktu = f"Estimasi Waktu Tempuh: {math.ceil(estimated_minutes_detour)} menit (via detour)"

            else: # Rute alternatif ditemukan, tapi rute asli gagal dihitung
                # Tampilkan info rute alternatif saja
                kecepatan_km_per_menit = 36 / 60
                estimated_minutes_detour = current_length_km / kecepatan_km_per_menit
                
                reasons_str = self.desc_marker[0]
                analysis_str = (
                    f"Analisis:\n"
                    f"Jaringan sedang dalam simulasi {reasons_str}. "
                    f"Rute alternatif yang ditemukan adalah {current_length_km:.2f} km. "
                    f"Estimasi waktu tempuh sekitar {math.ceil(estimated_minutes_detour)} menit (asumsi 36 km/jam)."
                )
                label_jarak = f"Jarak Tempuh (Alternatif): {current_length_km:.2f} km"
                label_waktu = f"Estimasi Waktu Tempuh: {math.ceil(estimated_minutes_detour)} menit"

        # --- JIKA TIDAK ADA SIMULASI (KONDISI NORMAL) ---
        else:
            if current_edges is None:
                # ... (Error handling rute normal tidak ditemukan, SAMA seperti sebelumnya) ...
                return None, None, None
                
            # Rute normal ditemukan
            kecepatan_km_per_menit = 36 / 60
            estimated_minutes_normal = current_length_km / kecepatan_km_per_menit
            
            analysis_str = (
                f"Analisis:\n"
                f"Rute terpendek dari '{start_name}' ke '{dest_name}' adalah {current_length_km:.2f} km. "
                f"Dengan asumsi kecepatan 36 km/jam, perjalanan ini diperkirakan memakan waktu sekitar {math.ceil(estimated_minutes_normal)} menit. "
                f"Waktu tempuh aktual dapat bervariasi."
            )
            label_jarak = f"Jarak Tempuh Total: {current_length_km:.2f} km"
            label_waktu = f"Estimasi Waktu Tempuh: {math.ceil(estimated_minutes_normal)} menit"

        # --- Update label UI DENGAN HASIL AKHIR ---
        self.lbl_distance.setText(label_jarak)
        self.lbl_timecalc.setText(label_waktu)
        self.map_desc.setText(analysis_str) # Pastikan label ini ada di _build_ui

        # Kembalikan hasil rute saat ini (normal atau detour)
        if current_edges:
            path_nodes = [current_edges[0][0]] + [e[1] for e in current_edges]
            return path_nodes, current_length_km, dest_name
        else:
            return None, None, None

    def _on_show_fastest_route(self):
        path_nodes, length_km, dest_name = self._compute_route()
        if not path_nodes:
            return
        dlg = RoutePreviewDialog(
            self.G,
            path_nodes,
            start_name="Depot Air Pusat",
            end_name=dest_name,
            length_km=length_km,
            title=f"Rute Tercepat: Depot Air Pusat → {dest_name} ({length_km:.2f} km)"
        )
        dlg.exec()

    def _on_show_nodes_timeline(self):
        path_nodes, _, dest_name = self._compute_route()
        if not path_nodes:
            return
        dlg = NodeTimelineDialog(self.gdf_lokasi, self.G, path_nodes, title=f"Timeline Dijkstra: Depot Air Pusat → {dest_name}")
        dlg.exec()

    def get_tingkat_kemacetan(self, waktu_kirim: datetime) -> float:
        jam = waktu_kirim.time()

        if time(0,0) <= jam < time(6,0):
            return 0
        elif time(6,0) <= jam < time(8,0):
            return 1
        elif time(8,0) <= jam < time(10,0):
            return 0.5
        elif time(10,0) <= jam < time(15,30):
            return 0.2
        elif time(15,30) <= jam < time(18,0):
            return 0.8
        elif time(18,0) <= jam < time(20,0):
            return 0.2
        else:
            return 0

    def get_max_speed_from_kemacetan(self, kemacetan: float) -> float:
        if kemacetan == 0:
            return 60
        elif kemacetan == 0.2:
            return 48
        elif kemacetan == 0.5:
            return 30
        elif kemacetan == 0.8:
            return 20
        elif kemacetan == 1.0:
            return 15

    def hitung_simulasi_kecepatan(self, jarak_km: float, waktu_kirim: datetime, jumlah_tikungan: int):
        kemacetan = self.get_tingkat_kemacetan(waktu_kirim)
        max_speed = self.get_max_speed_from_kemacetan(kemacetan)
        min_speed = 15
        base_speed = 45
        speed = base_speed

        total_waktu_detik = 0

        # Simulasi hingga jarak habis
        while jarak_km > 0:
            total_waktu_detik += 10  # setiap step = 10 detik

            # random naik atau turun
            arah = random.choice(["up", "down"])

            if arah == "up":
                speed += 5
            else:
                speed -= 5

            # apply batas dinamis
            if speed > max_speed:
                speed = max_speed
            if speed < min_speed:
                speed = min_speed

            # hitung jarak yang ditempuh di interval 10 detik
            jarak_tempuh = speed * (10 / 3600)
            jarak_km -= jarak_tempuh
        
        # 6. tambahan waktu akibat tikungan (tiap tikungan 3 detik @ 20km/jam)
        waktu_tikungan = jumlah_tikungan * (3 / 3600)
        total_waktu_detik += waktu_tikungan

        return total_waktu_detik



class RoutePreviewDialog(QDialog):
    def __init__(self, g: nx.Graph, path_nodes: list, start_name: str = "START", end_name: str = "FINISH", length_km: float | None = None, title: str = "Rute Tercepat", parent=None):
        super().__init__(parent)
        self.G = g
        self.path_nodes = path_nodes
        self.start_name = start_name
        self.end_name = end_name
        self.length_km = length_km
        self.setWindowTitle("Rute Tercepat")
        self.resize(900, 650)
        layout = QVBoxLayout(self)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("SectionTitle")
        layout.addWidget(lbl_title)

        # Figure & Canvas dalam ScrollArea
        self.fig, self.ax = plt.subplots(figsize=(12, 9))
        self.canvas = FigureCanvas(self.fig)
        scroll = QScrollArea()
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.canvas)
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, stretch=1)

        # Tombol kembali
        btn = QPushButton("Kembali")
        btn.setObjectName("Secondary")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

        self._draw_route()

    # def _draw_route(self):
    #     # Plot langsung ke axes dialog agar stabil
    #     self.ax.clear()
    #     ox.plot_graph_route(
    #         self.G,
    #         self.path_nodes,
    #         route_color='red',
    #         route_linewidth=4,
    #         node_size=0,
    #         bgcolor='#FFFFFF',
    #         show=False,
    #         close=False,
    #         ax=self.ax
    #     )
    #     # Tambahkan label START/FINISH dan panah arah seperti di path_finder
    #     try:
    #         if self.path_nodes:
    #             start_node = self.path_nodes[0]
    #             end_node = self.path_nodes[-1]
    #             start_x = self.G.nodes[start_node]['x']
    #             start_y = self.G.nodes[start_node]['y']
    #             end_x = self.G.nodes[end_node]['x']
    #             end_y = self.G.nodes[end_node]['y']
    #             # Label START
    #             self.ax.text(
    #                 start_x,
    #                 start_y,
    #                 f"  START\n  {self.start_name}",
    #                 fontsize=9,
    #                 color='white',
    #                 bbox=dict(facecolor='green', alpha=0.8, boxstyle="round,pad=0.3")
    #             )
    #             # Label FINISH
    #             self.ax.text(
    #                 end_x,
    #                 end_y,
    #                 f"  FINISH\n  {self.end_name}",
    #                 fontsize=9,
    #                 color='white',
    #                 bbox=dict(facecolor='darkred', alpha=0.8, boxstyle="round,pad=0.3")
    #             )
    #             # Panah menuju FINISH
    #             if len(self.path_nodes) >= 2:
    #                 second_last = self.path_nodes[-2]
    #                 sl_x = self.G.nodes[second_last]['x']
    #                 sl_y = self.G.nodes[second_last]['y']
    #                 self.ax.annotate(
    #                     "",
    #                     xy=(end_x, end_y),
    #                     xytext=(sl_x, sl_y),
    #                     arrowprops=dict(arrowstyle="->", color="gold", linewidth=3, shrinkA=5, shrinkB=5)
    #                 )
    #         # Title
    #         if self.length_km is not None:
    #             self.ax.set_title(f"Rute Tercepat: {self.start_name} -> {self.end_name} ({self.length_km:.2f} km)")
    #     except Exception:
    #         pass
    #     self.ax.set_aspect('equal')
    #     self.canvas.draw()

    def _draw_route(self):
        # Bersihkan kanvas
        self.ax.clear()
        
        # Konversi graf OSMnx ke GeoDataFrame
        # hanya menerima satu variabel `edges_gdf`
        edges_gdf = ox.graph_to_gdfs(self.G, nodes=False, edges=True)
        
        # Gambar semua jalan (latar belakang)
        edges_gdf.plot(ax=self.ax, color='gray', linewidth=1, alpha=0.6)
        
        # Buat sub-graf rute dan gambar di atasnya
        route_graph = self.G.subgraph(self.path_nodes)
        # hanya menerima satu variabel `route_edges_gdf`
        route_edges_gdf = ox.graph_to_gdfs(route_graph, nodes=False, edges=True)
        
        # Gambar sisi rute terpendek di atasnya dengan warna merah
        if not route_edges_gdf.empty:
            route_edges_gdf.plot(ax=self.ax, color='red', linewidth=3)

        # Tambahkan label START/FINISH dan panah arah (logika ini sama seperti sebelumnya)
        try:
            if self.path_nodes:
                start_node = self.path_nodes[0]
                end_node = self.path_nodes[-1]
                start_x, start_y = self.G.nodes[start_node]['x'], self.G.nodes[start_node]['y']
                end_x, end_y = self.G.nodes[end_node]['x'], self.G.nodes[end_node]['y']
                
                # Label START
                self.ax.text(
                    start_x, start_y, f"  START\n  {self.start_name}", fontsize=9, color='white',
                    bbox=dict(facecolor='green', alpha=0.8, boxstyle="round,pad=0.3")
                )
                # Label FINISH
                self.ax.text(
                    end_x, end_y, f"  FINISH\n  {self.end_name}", fontsize=9, color='white',
                    bbox=dict(facecolor='darkred', alpha=0.8, boxstyle="round,pad=0.3")
                )
                # Panah menuju FINISH
                if len(self.path_nodes) >= 2:
                    second_last = self.path_nodes[-2]
                    sl_x, sl_y = self.G.nodes[second_last]['x'], self.G.nodes[second_last]['y']
                    self.ax.annotate(
                        "", xy=(end_x, end_y), xytext=(sl_x, sl_y),
                        arrowprops=dict(arrowstyle="->", color="gold", linewidth=3, shrinkA=15, shrinkB=15)
                    )
        except Exception as e:
            print(f"Gagal menambahkan anotasi: {e}")
            
        # Atur tampilan akhir dan perbarui kanvas
        self.ax.set_aspect('equal')
        self.ax.axis('off')
        self.fig.tight_layout(pad=0)
        self.canvas.draw()


class NodeTimelineDialog(QDialog):
    def __init__(self, gdf_lokasi: gpd.GeoDataFrame, G, path_nodes: list, title: str = "Timeline Dijkstra", parent=None):
        super().__init__(parent)
        self.gdf_lokasi = gdf_lokasi
        self.path_nodes = path_nodes
        self.G = G
        self.setWindowTitle("Timeline Dijkstra")
        self.resize(900, 650)
        layout = QVBoxLayout(self)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("SectionTitle")
        layout.addWidget(lbl_title)

        self.fig, self.ax = plt.subplots(figsize=(12, 9))
        self.canvas = FigureCanvas(self.fig)
        scroll = QScrollArea()
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.canvas)
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, stretch=1)

        btn = QPushButton("Kembali")
        btn.setObjectName("Secondary")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

        self._draw_timeline()

    def _draw_timeline(self):
        # Bersihkan axes yang sudah ada
        self.ax.clear()

        print("Membuat visualisasi timeline rute yang fleksibel...")

        # --- Langkah 1: Siapkan Informasi Label Simpul ---
        nama_simpul_map = self.gdf_lokasi.set_index('osmid')['intersection_name'].to_dict()
        node_labels = {}
        for node_id in self.path_nodes:
            nama = nama_simpul_map.get(node_id, str(node_id))
            node_labels[node_id] = textwrap.fill(nama, width=20)

        # --- Langkah 2: Buat Layout Zig-Zag ---
        pos = {}
        nodes_per_row = 5
        x, y = 0, 0
        direction = 1
        for i, node_id in enumerate(self.path_nodes):
            pos[node_id] = (x, y)
            if (i + 1) % nodes_per_row == 0 and i < len(self.path_nodes) - 1:
                y -= 2
                direction *= -1
            else:
                x += direction

        # --- Langkah 3: Siapkan Label Bobot Sisi ---
        edge_labels = {}
        for i in range(len(self.path_nodes) - 1):
            u, v = self.path_nodes[i], self.path_nodes[i+1]
            # Ambil data sisi dari graf peta ASLI (G_peta)
            panjang_meter = self.G.get_edge_data(u, v)[0]['length']
            panjang_km = f"{panjang_meter / 1000:.2f} km"
            edge_labels[(u, v)] = panjang_km

        # --- Langkah 4: Buat Graf Rute dan Gambar ---
        G_rute = nx.path_graph(self.path_nodes)
        
        # Gambar simpul
        nx.draw_networkx_nodes(G_rute, pos, ax=self.ax, node_color='skyblue', node_size=500)
        
        # Gambar sisi
        nx.draw_networkx_edges(G_rute, pos, ax=self.ax, width=2.0, edge_color='black', arrows=True, arrowsize=20, arrowstyle='-|>')
        
        # Gambar label bobot pada sisi
        nx.draw_networkx_edge_labels(
            G_rute, pos,
            edge_labels=edge_labels,
            font_color='red',
            font_size=8,
            ax=self.ax
        )
        
        # Gambar label nama di bawah simpul
        for i, node_id in enumerate(self.path_nodes):
            x_coord, y_coord = pos[node_id]
            label_text = f"{i+1}\n{node_labels[node_id]}"
            self.ax.text(x_coord, y_coord - 0.5, label_text, ha='center', va='top', fontsize=8)

        self.ax.axis('off')
        self.ax.set_title("Konfirmasi Rute Pengantaran (Timeline Perjalanan)", fontsize=16, pad=20)
        
        # Update layout dan render canvas, jangan pakai plt.show()
        self.fig.tight_layout()
        self.canvas.draw()
