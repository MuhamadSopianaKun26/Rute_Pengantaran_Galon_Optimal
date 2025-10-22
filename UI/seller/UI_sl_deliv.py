from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame,
    QListWidget, QListWidgetItem, QPushButton, QSpacerItem, QSizePolicy, QMessageBox, QScrollArea
)
import os, json, datetime
import math
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import geopandas as gpd
import osmnx as ox
import textwrap
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

    def __init__(self, order: dict, parent=None):
        super().__init__(parent)
        self.order = order or {}
        self._price_map = _load_products_price_map()

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

        # Bagian atas: Placeholder Map (5 bagian)
        self.map_box = QFrame()
        self.map_box.setObjectName("MapBox")
        map_layout = QVBoxLayout(self.map_box)
        map_layout.setContentsMargins(16, 16, 16, 16)
        map_layout.setSpacing(8)
        map_title = QLabel("Map Rute Pengiriman")
        map_title.setObjectName("SectionTitle")
        map_desc = QLabel("Visualisasi rute akan ditampilkan di jendela terpisah saat Anda menekan tombol di bawah.")
        map_desc.setStyleSheet("color:#5A8A9B;")
        map_desc.setWordWrap(True)
        map_layout.addWidget(map_title)
        map_layout.addWidget(map_desc)
        # Label hasil perhitungan rute
        self.lbl_distance = QLabel("Jarak tempuh: -")
        self.lbl_timecalc = QLabel("Estimasi waktu (100 m/s): -")
        self.lbl_distance.setStyleSheet("color:#2C5F6F;font-weight:600;")
        self.lbl_timecalc.setStyleSheet("color:#2C5F6F;")
        map_layout.addWidget(self.lbl_distance)
        map_layout.addWidget(self.lbl_timecalc)
        map_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

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

        self.lbl_eta_duration = QLabel()
        self.lbl_eta_duration.setStyleSheet("color:#2C5F6F;")
        self.lbl_eta_arrival = QLabel()
        self.lbl_eta_arrival.setStyleSheet("color:#2C5F6F;")

        info_layout.addWidget(self.lbl_buyer)
        info_layout.addWidget(self.lbl_address)
        info_layout.addSpacing(8)
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

        # Estimasi
        duration_min = self._estimate_duration_minutes()
        self.lbl_eta_duration.setText(f"Estimasi Waktu Pengiriman: {duration_min} menit")
        arrival_str = self._estimate_arrival_hhmm(duration_min)
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
            self.G, self.gdf_lokasi = G, gdf
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
            return None, None, None
        start_name = "Depot Air Pusat"
        dest_name = self._get_destination_name()
        if not dest_name:
            QMessageBox.information(self, "Tujuan Tidak Ditemukan", "Alamat tujuan pembeli tidak tersedia.")
            return None, None, None
        edges, length_km = cari_rute_by_nama(self.G, self.gdf_lokasi, start_name, dest_name, show_preview=False)
        if not edges:
            QMessageBox.information(self, "Rute Tidak Ditemukan", f"Tidak ada rute dari {start_name} ke {dest_name}.")
            return None, None, None
        # Rekonstruksi nodes dari edges
        path_nodes = [edges[0][0]] + [e[1] for e in edges]
        # Update label jarak & estimasi waktu (100 m/s)
        self.lbl_distance.setText(f"Jarak tempuh: {length_km:.2f} km")
        seconds = (length_km * 1000.0) / 100.0
        self.lbl_timecalc.setText(f"Estimasi waktu (100 m/s): {seconds:.1f} detik")
        return path_nodes, length_km, dest_name

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
    def __init__(self, gdf_lokasi: gpd.GeoDataFrame, G: nx.Graph, path_nodes: list, title: str = "Timeline Dijkstra", parent=None):
        super().__init__(parent)
        self.gdf_lokasi = gdf_lokasi
        self.G = G
        self.path_nodes = path_nodes
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

