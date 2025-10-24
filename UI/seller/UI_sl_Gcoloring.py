import math
import os
import json
import networkx as nx
import matplotlib.pyplot as plt
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QComboBox, QScrollArea, QWidget, QSizePolicy, QMessageBox # Added QMessageBox
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

try:
    # Asumsi timeline ada di logic.graph atau sesuaikan path-nya
    from logic.graph.path_finder import buat_visualisasi_timeline_dijkstra
except ImportError:
    print("PERINGATAN: Fungsi buat_visualisasi_timeline_dijkstra tidak ditemukan.")
    # Buat dummy function agar tidak error
    def buat_visualisasi_timeline_dijkstra(*args, **kwargs):
        print("Fungsi visualisasi timeline tidak tersedia.")
        QMessageBox.warning(None, "Timeline Error", "Fungsi untuk menampilkan timeline tidak ditemukan.")

# [MODIFIKASI] Use try-except for robust imports
try:
    from logic.graph.graph_coloring import build_order_graph_from_json, color_graph_with_capacity
    # Assume path_finder is in the same directory as graph_coloring
    from logic.graph.path_finder import muat_data_peta_dan_lokasi, cari_rute_by_nama
    # Assume RoutePreviewDialog is in UI.seller
    from UI.seller.UI_sl_deliv import RoutePreviewDialog
except ImportError as e:
    print(f"CRITICAL IMPORT ERROR: {e}. Route functionality will be disabled.")
    # Provide dummy fallbacks
    def muat_data_peta_dan_lokasi(*args, **kwargs): return None, None
    def cari_rute_by_nama(*args, **kwargs): return (None, 0)
    def build_order_graph_from_json(*args, **kwargs): return nx.Graph()
    def color_graph_with_capacity(*args, **kwargs): return {}, {}
    class RoutePreviewDialog(QDialog):
         def __init__(self, g, path, title="", parent=None):
            super().__init__(parent)
            self.setWindowTitle("Preview Rute (Error)")
            layout = QVBoxLayout(self)
            lbl = QLabel(f"ERROR: Could not load RoutePreviewDialog.\nRoute data:\n{title}\nNodes: {path}")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
            btn = QPushButton("Close")
            btn.clicked.connect(self.accept)
            layout.addWidget(btn)

def _db_path(filename: str) -> str:
    # Assuming this file is in UI/seller, go up 3 levels
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, 'Database', filename)

class OrderPreviewDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # [BARU] Attributes to store map graph and location data
        self.G = None
        self.gdf_lokasi = None
        self.G_awal = None # Keep original graph for routing
        self.gdf_lokasi_awal = None
        self.address_map = {} # Map Customer Name -> Intersection Name
        self.bins = {} # Store coloring results

        self.setWindowTitle("Preview Orderan")
        self.resize(1000, 720)
        self.setModal(True)
        self.setStyleSheet(
            """
            QDialog { background: #F8F9FA; }
            QLabel#Title { font-size: 20px; font-weight: 800; color: #2C5F6F; }
            QLabel#SectionTitle { font-size: 14px; font-weight: 700; color: #2C5F6F; }
            QFrame#MapBox { background: white; border: 2px dashed #5A8A9B; border-radius: 12px; }
            QFrame#InfoBox { background: white; border: 1px solid rgba(0,0,0,0.06); border-radius: 12px; }
            QPushButton#Primary { background: #2196F3; color: white; font-weight: 700; padding: 10px 18px; border-radius: 8px; }
            QPushButton#Primary:hover { background: #1E88E5; }
            QPushButton#Secondary { background: white; color: #2C5F6F; font-weight: 600; padding: 10px 18px; border: 1px solid #5A8A9B; border-radius: 8px; }
            QPushButton#Secondary:hover { background: #E3F2FD; }
            /* [BARU] Style for clickable bin buttons */
            QPushButton#BinButton {
                background-color: #E8F5E9; /* Light green */
                color: #1B5E20; /* Dark green text */
                border: 1px solid #A5D6A7;
                border-radius: 6px;
                padding: 8px 12px;
                text-align: left;
                font-weight: 600;
                font-size: 11px; /* Slightly smaller font */
            }
            QPushButton#BinButton:hover {
                background-color: #C8E6C9;
            }
            """
        )
        self._build_ui()
        try:
            self.cmb_schedule.currentTextChanged.connect(self._load_and_render_orders)
        except Exception as e:
            print(f"Error connecting schedule change signal: {e}")

        # Initial load for the default schedule
        self._load_and_render_orders()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Preview Orderan")
        title.setObjectName("Title")
        layout.addWidget(title)

        # --- Schedule Selector ---
        schedule_row = QHBoxLayout()
        schedule_row.setSpacing(8)
        lbl = QLabel("Jadwal:")
        lbl.setStyleSheet("color:#2C5F6F;font-weight:700;")
        self.cmb_schedule = QComboBox()
        # [MODIFIKASI] Use title case for display, keep internal lowercase
        self.cmb_schedule.addItems(["Segera", "09.00", "12.00", "15.00", "18.00"])
        self.cmb_schedule.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        schedule_row.addWidget(lbl)
        schedule_row.addWidget(self.cmb_schedule)
        schedule_row.addStretch(1)
        layout.addLayout(schedule_row)

        # --- Order List Box ---
        self.map_box = QFrame()
        self.map_box.setObjectName("MapBox")
        map_layout = QVBoxLayout(self.map_box)
        map_layout.setContentsMargins(16, 16, 16, 16); map_layout.setSpacing(10)
        map_title = QLabel("Daftar Pesanan (sesuai jadwal)"); map_title.setObjectName("SectionTitle"); map_layout.addWidget(map_title)
        self.orders_scroll = QScrollArea(); self.orders_scroll.setWidgetResizable(True); self.orders_container = QWidget(); self.orders_layout = QVBoxLayout(self.orders_container); self.orders_layout.setContentsMargins(0, 0, 0, 0); self.orders_layout.setSpacing(6)
        self.lbl_orders = QLabel("Pilih jadwal untuk menampilkan daftar."); self.lbl_orders.setWordWrap(True); self.orders_layout.addWidget(self.lbl_orders); self.orders_layout.addStretch(1); self.orders_scroll.setWidget(self.orders_container); map_layout.addWidget(self.orders_scroll)
        self.map_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.map_box.setFixedHeight(250) # Reduced height
        layout.addWidget(self.map_box, stretch=0)

        # --- Optimal Delivery Box (with clickable buttons) ---
        self.opt_box = QFrame()
        self.opt_box.setObjectName("InfoBox")
        opt_layout = QVBoxLayout(self.opt_box)
        opt_layout.setContentsMargins(16, 16, 16, 16); opt_layout.setSpacing(8)
        opt_title = QLabel("Urutan Pengiriman Optimal (Klik grup untuk lihat rute)"); opt_title.setObjectName("SectionTitle")

        # [MODIFIKASI] Scroll area for bin buttons
        self.optimal_scroll = QScrollArea()
        self.optimal_scroll.setWidgetResizable(True)
        self.optimal_container = QWidget()
        self.optimal_layout = QVBoxLayout(self.optimal_container) # This holds the buttons
        self.optimal_layout.setContentsMargins(4, 4, 4, 4); self.optimal_layout.setSpacing(6)
        self.lbl_optimal_placeholder = QLabel("Lakukan Graph Coloring terlebih dahulu.")
        self.lbl_optimal_placeholder.setWordWrap(True); self.optimal_layout.addWidget(self.lbl_optimal_placeholder); self.optimal_layout.addStretch(1)
        self.optimal_scroll.setWidget(self.optimal_container)

        opt_layout.addWidget(opt_title)
        opt_layout.addWidget(self.optimal_scroll) # Add scroll area
        layout.addWidget(self.opt_box, stretch=3) # Increased stretch

        # --- Action Buttons ---
        btn_row = QHBoxLayout()
        self.btn_do_gc = QPushButton("Lakukan Graph Coloring"); self.btn_do_gc.setObjectName("Primary"); btn_row.addWidget(self.btn_do_gc)
        btn_row.addStretch(1)
        self.btn_back = QPushButton("Kembali"); self.btn_back.setObjectName("Secondary"); btn_row.addWidget(self.btn_back)
        layout.addLayout(btn_row)

        # --- Connections ---
        self.btn_back.clicked.connect(self.reject)
        self.btn_do_gc.clicked.connect(self._perform_graph_coloring) # Changed target function

    def _normalize_schedule(self, s: str) -> str:
        s = (s or '').strip().lower()
        if s == 'segera': return 'segera' # Keep 'segera' as is
        s = s.replace(':', '.')
        # Ensure format like 09.00
        parts = s.split('.')
        if len(parts) == 2 and len(parts[0]) == 2 and len(parts[1]) == 2:
            return s
        return 'segera' # Fallback to 'segera' if format is wrong

    def _load_and_render_orders(self):
        # (This function remains mostly the same, loads orders for the list view)
        path = _db_path('order_data.json')
        try:
            with open(path, 'r', encoding='utf-8') as f: data = json.load(f) or []
        except Exception as e:
            print(f"Error loading order_data.json: {e}"); data = []

        selected = self._normalize_schedule(self.cmb_schedule.currentText())
        lines = []
        order_found = False
        for order in data:
            status = (order.get('status') or '').strip().lower()
            # [MODIFIKASI] Match 'menunggu' status as well for previewing
            if status not in ['sedang_disiapkan', 'menunggu']: continue

            sch_raw = str(order.get('schedule', 'segera')) # Default to 'segera'
            sch = self._normalize_schedule(sch_raw)

            # Match 'segera' or the specific time
            if sch != selected: continue

            order_found = True
            name = order.get('customer_name') or '-'; street = order.get('street') or ''; area = order.get('area') or ''; dest = street if street else (area or '-')
            items = order.get('items') or []; parts = []
            for it in items: nm = str(it.get('name', 'Item')); qty = it.get('qty', 0); parts.append(f"{nm} ({qty})") # Show qty clearly
            lines.append(f"👤 **{name}** - Tujuan: {dest}")
            lines.append(f"   Items: {', '.join(parts)}")
            lines.append("-" * 20) # Separator

        # Clear previous optimal routes when schedule changes
        self._clear_optimal_layout()
        self.lbl_optimal_placeholder = QLabel("Lakukan Graph Coloring untuk jadwal ini.")
        self.optimal_layout.addWidget(self.lbl_optimal_placeholder)
        self.optimal_layout.addStretch(1)

        if not order_found:
            text = f"Tidak ada pesanan dengan status 'Menunggu' atau 'Sedang Disiapkan' untuk jadwal '{selected}'."
        else:
             text = "\n".join(lines).strip()

        self.lbl_orders.setText(text)
        self.lbl_orders.setTextFormat(Qt.TextFormat.MarkdownText) # Allow simple formatting


    # [MODIFIKASI] Renamed and enhanced function
    def _perform_graph_coloring(self):
        """Performs graph coloring and updates the UI with clickable bins."""
        current_schedule = self._normalize_schedule(self.cmb_schedule.currentText())
        print(f"Performing Graph Coloring for schedule: {current_schedule}")
        orders_simple = self._collect_filtered_orders(current_schedule)

        if not orders_simple:
             QMessageBox.information(self, "Tidak Ada Pesanan", f"Tidak ada pesanan yang cocok (status 'Menunggu'/'Sedang Disiapkan') untuk jadwal '{current_schedule}' untuk diwarnai.")
             self._clear_optimal_layout()
             self.lbl_optimal_placeholder = QLabel(f"Tidak ada pesanan untuk jadwal '{current_schedule}'.")
             self.optimal_layout.addWidget(self.lbl_optimal_placeholder)
             self.optimal_layout.addStretch(1)
             return

        # Store address mapping needed for routing later
        self.address_map = {
            str(o.get('name')): str(o.get('intersection_name'))
            for o in orders_simple if o.get('intersection_name')
        }

        # Show the preview dialog (contains the coloring logic)
        dlg = GraphColoringPreview(orders_simple, self)
        dlg.exec()

        # Update the main dialog's optimal section based on results
        self.bins = getattr(dlg, 'bins', {}) or {} # Get bins from the preview dialog
        self._update_optimal_layout(orders_simple)


    def _update_optimal_layout(self, orders_simple_list):
        """Updates the 'Urutan Pengiriman Optimal' section with buttons."""
        self._clear_optimal_layout() # Clear previous buttons/labels

        if not self.bins:
            self.lbl_optimal_placeholder = QLabel("Graph coloring tidak menghasilkan grup pengiriman.")
            self.optimal_layout.addWidget(self.lbl_optimal_placeholder)
            self.optimal_layout.addStretch(1)
            return

        # Helper maps (copied from your original _open_gc_preview)
        name_map = {str(o.get('id')): str(o.get('name') or o.get('id')) for o in orders_simple_list}
        gal_map = {str(o.get('id')): int(o.get('galon', 0)) for o in orders_simple_list}
        box_map = {str(o.get('id')): int(o.get('kardus', 0)) for o in orders_simple_list}

        print(f"Updating optimal layout with {len(self.bins)} bins.")
        for cid in sorted(self.bins.keys()):
            nodes = self.bins[cid].get('nodes', [])
            customer_names_in_bin = [name_map.get(str(n), f"ID:{n}") for n in nodes]

            total_g = sum(gal_map.get(str(n), 0) for n in nodes)
            total_k = sum(box_map.get(str(n), 0) for n in nodes)

            # Create button text
            btn_text = (f"🚚 **Grup {cid + 1}:** {', '.join(customer_names_in_bin)}\n"
                        f"   (Load: {total_g} Galon, {total_k} Kardus)")

            bin_button = QPushButton(btn_text)
            bin_button.setObjectName("BinButton")
            bin_button.setCursor(Qt.CursorShape.PointingHandCursor)
            # Use lambda to capture the customer names for this specific button
            bin_button.clicked.connect(
                lambda checked=False, names=customer_names_in_bin: self._calculate_and_show_route(names)
            )
            self.optimal_layout.addWidget(bin_button)

        self.optimal_layout.addStretch(1)

    def _clear_optimal_layout(self):
         """Removes all widgets from the optimal_layout."""
         while self.optimal_layout.count():
            child = self.optimal_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


    # [MODIFIKASI] Accepts schedule argument, includes intersection_name
    def _collect_filtered_orders(self, target_schedule: str):
        path = _db_path('order_data.json')
        try:
            with open(path, 'r', encoding='utf-8') as f: data = json.load(f) or []
        except Exception: data = []

        result = []
        used_ids = set()
        for idx, order in enumerate(data):
            status = (order.get('status') or '').strip().lower()
            # Only consider these statuses for coloring/routing
            if status not in ['sedang_disiapkan', 'menunggu']: continue

            sch_raw = str(order.get('schedule', 'segera'))
            sch = self._normalize_schedule(sch_raw)
            if sch != target_schedule: continue

            # Ensure unique ID, fallback using index if necessary
            oid_base = order.get('id') or order.get('order_id') or order.get('customer_name')
            oid = str(oid_base if oid_base else f"order_{idx}")
            count = 1
            final_oid = oid
            while final_oid in used_ids:
                final_oid = f"{oid}_{count}"
                count += 1
            used_ids.add(final_oid)

            name = order.get('customer_name') or f"Pelanggan_{idx}"

            # IMPORTANT: Get the address (street)
            address = order.get('street') or "Unknown Address"
            if not address or address == "Unknown Address":
                 print(f"Warning: Order for {name} (ID: {final_oid}) missing valid street/intersection name.")


            galon_qty = 0; kardus_qty = 0
            for it in (order.get('items') or []):
                nm = str(it.get('name', '')).lower()
                qty = int(it.get('qty', 0) or 0)
                if 'galon' in nm: galon_qty += qty
                if 'box' in nm or 'kardus' in nm: kardus_qty += qty

            result.append({
                'id': final_oid, # Use the guaranteed unique ID
                'galon': galon_qty,
                'kardus': kardus_qty,
                'name': name,
                'intersection_name': address # Store the address for routing
            })
        print(f"Collected {len(result)} orders for schedule '{target_schedule}'.")
        return result


    # --- [BARU] Map Loading and Routing Logic (adapted from your snippet) ---

    def _load_graph_if_needed(self):
        """Loads the map graph (G) and GeoDataFrame (gdf) if not already loaded."""
        # Check if graphs are already loaded
        if self.G_awal is not None and self.gdf_lokasi_awal is not None:
             print("[DEBUG] Map graph already loaded.")
             return True # Indicate success

        print("[DEBUG] Attempting to load map graph and GeoJSON...")
        lokasi_peta = (-6.872, 107.578) # Center point for OSMnx
        path_geojson = "logic/graph/output.geojson"

        try:
            if not os.path.exists(path_geojson):
                QMessageBox.warning(self, "GeoJSON Not Found", f"Required file not found:\n{path_geojson}")
                self.G, self.gdf_lokasi, self.G_awal, self.gdf_lokasi_awal = None, None, None, None
                return False # Indicate failure

            # Call the imported function
            G, gdf = muat_data_peta_dan_lokasi(lokasi_peta, path_ke_geojson=path_geojson)

            if G is None or gdf is None:
                 QMessageBox.critical(self, "Map Load Failed", "Failed to load map data using muat_data_peta_dan_lokasi.")
                 self.G, self.gdf_lokasi, self.G_awal, self.gdf_lokasi_awal = None, None, None, None
                 return False

            # Store the original graph data for routing
            self.G = G # Current G (might be modified by simulation later if needed)
            self.gdf_lokasi = gdf
            self.G_awal = G.copy()
            self.gdf_lokasi_awal = gdf.copy()
            print("[DEBUG] Map graph and GDF loaded successfully.")
            return True # Indicate success

        except Exception as e:
            QMessageBox.critical(self, "Error Loading Map", f"An unexpected error occurred while loading map data: {e}")
            self.G, self.gdf_lokasi, self.G_awal, self.gdf_lokasi_awal = None, None, None, None
            return False # Indicate failure

    def _calculate_and_show_route(self, customer_names: list):
        """
        Calculates the sequential shortest path and displays the map route
        WITH customer highlights. Does NOT show a separate timeline.
        """
        print(f"Calculating route for bin: {customer_names}")

        if not self._load_graph_if_needed():
            QMessageBox.warning(self, "Map Data Error", "Cannot calculate route: map data failed to load.")
            return

        start_node_name = "Pusat Depot Galon" # <<<=== SESUAIKAN JIKA PERLU
        stops_names = [start_node_name]
        valid_stops = True
        customer_intersection_names = []
        for name in customer_names:
            address = self.address_map.get(name)
            if not address or address == "Unknown Address":
                QMessageBox.warning(self, "Missing Address", f"Cannot find address for customer: '{name}'. Route calculation aborted.")
                valid_stops = False
                break
            stops_names.append(address)
            customer_intersection_names.append(address)

        if not valid_stops: return
        print(f"Route stops (intersection names): {stops_names}")

        total_route_nodes = []
        total_distance_km = 0.0
        route_possible = True

        try:
            current_graph = self.G_awal
            current_gdf = self.gdf_lokasi_awal

            if current_graph is None or current_gdf is None:
                raise ValueError("Original map graph (G_awal) or gdf_lokasi_awal is not loaded.")

            for i in range(len(stops_names) - 1):
                start_name_segment = stops_names[i]
                end_name_segment = stops_names[i + 1]
                print(f"  Calculating segment: {start_name_segment} -> {end_name_segment}")
                edges, length_km = cari_rute_by_nama(current_graph, current_gdf, start_name_segment, end_name_segment, show_preview=False)
                if edges is None:
                    QMessageBox.critical(self, "Route Segment Failed", f"Could not find path between '{start_name_segment}' and '{end_name_segment}'.")
                    route_possible = False; break
                path_nodes_segment = [edges[0][0]] + [edge[1] for edge in edges]
                print(f"    Segment found: {length_km:.2f} km, {len(path_nodes_segment)} nodes")
                total_distance_km += length_km
                if i == 0: total_route_nodes.extend(path_nodes_segment)
                else: total_route_nodes.extend(path_nodes_segment[1:])

            if not route_possible: return

            # --- Persiapan ID Pelanggan (Tetap diperlukan) ---
            customer_destination_ids = []
            name_to_id_map = {}
            if current_gdf is not None and not current_gdf.empty:
                 try:
                      gdf_indexed_by_name = current_gdf.set_index('intersection_name')
                      name_to_id_map = gdf_indexed_by_name['osmid'].to_dict()
                 except Exception as e: print(f"Error making name_to_id_map: {e}")

            for intersection_name in customer_intersection_names:
                node_id = name_to_id_map.get(intersection_name)
                if node_id is not None: customer_destination_ids.append(node_id)
                else: print(f"Warning: Cannot find OSM ID for '{intersection_name}'")
            # --- Selesai Persiapan ID ---

            # 4. Display the combined route MAP in the preview dialog
            route_title = f"Rute Grup: {', '.join(customer_names)}\nTotal Jarak: {total_distance_km:.2f} km"
            print(f"Displaying MAP route with {len(total_route_nodes)} total nodes.")
            print(f"Highlighting customer OSM IDs: {customer_destination_ids}")

            # [MODIFIKASI] Kirim customer_destination_ids ke RoutePreviewDialog
            route_dialog = RoutePreviewDialog(
                g=current_graph,
                path_nodes=total_route_nodes,
                customer_node_ids=customer_destination_ids, # <-- KIRIM ID PELANGGAN
                title=route_title,
                parent=self
            )
            route_dialog.exec() # Tampilkan dialog peta

            # 5. [HAPUS] Pemanggilan ke buat_visualisasi_timeline_dijkstra dihapus

        except ValueError as ve:
             QMessageBox.critical(self, "Map Data Error", str(ve))
             print(f"ERROR calculating route: {ve}")
        except Exception as e:
            QMessageBox.critical(self, "Route Calculation Error", f"An error occurred: {e}")
            print(f"ERROR calculating route: {e}")

# --- (Kelas GraphColoringPreview Anda tetap sama persis) ---
class GraphColoringPreview(QDialog):
    def __init__(self, orders_simple: list, parent=None):
        super().__init__(parent)
        self.orders_simple = orders_simple or []
        self.name_map = {str(o.get('id')): str(o.get('name') or o.get('id')) for o in self.orders_simple}
        self.G = None
        self.coloring = {}
        self.bins = {}
        self.setWindowTitle("Preview Graph Coloring")
        self.resize(1000, 750)
        self.setModal(True)
        self.setStyleSheet(
            """
            QDialog { background: #F8F9FA; }
            QLabel#Title { font-size: 18px; font-weight: 800; color: #2C5F6F; }
            QFrame#CanvasBox { background: white; border: 1px solid rgba(0,0,0,0.08); border-radius: 12px; }
            QFrame#InfoBox { background: white; border: 1px solid rgba(0,0,0,0.06); border-radius: 12px; }
            QPushButton#Secondary { background: white; color: #2C5F6F; font-weight: 600; padding: 10px 18px; border: 1px solid #5A8A9B; border-radius: 8px; }
            QPushButton#Secondary:hover { background: #E3F2FD; }
            """
        )
        self._build_ui()
        self._render_graph_coloring()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        title = QLabel("Hasil Graph Coloring"); title.setObjectName("Title"); layout.addWidget(title)
        self.canvas_box = QFrame(); self.canvas_box.setObjectName("CanvasBox"); canvas_layout = QVBoxLayout(self.canvas_box); canvas_layout.setContentsMargins(16, 16, 16, 16); canvas_layout.setSpacing(8); self.fig, self.ax = plt.subplots(figsize=(16, 12)); self.canvas = FigureCanvas(self.fig)
        self.graph_scroll = QScrollArea(); self.graph_scroll.setWidgetResizable(True); self.graph_container = QWidget(); self.graph_container_layout = QVBoxLayout(self.graph_container); self.graph_container_layout.setContentsMargins(0, 0, 0, 0); self.graph_container_layout.addWidget(self.canvas); self.graph_scroll.setWidget(self.graph_container); canvas_layout.addWidget(self.graph_scroll); layout.addWidget(self.canvas_box, stretch=5)
        self.explain_scroll = QScrollArea(); self.explain_scroll.setWidgetResizable(True); self.explain_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding); self.explain_container = QWidget(); explain_container_layout = QVBoxLayout(self.explain_container); explain_container_layout.setContentsMargins(0, 0, 0, 0); explain_container_layout.setSpacing(12)
        self.summary_box = QFrame(); self.summary_box.setObjectName("InfoBox"); summary_layout = QVBoxLayout(self.summary_box); summary_layout.setContentsMargins(16, 16, 16, 16); summary_layout.setSpacing(8); summary_title = QLabel("Ringkasan Coloring"); summary_title.setObjectName("SectionTitle"); self.lbl_summary = QLabel(""); self.lbl_summary.setWordWrap(True); self.lbl_bins = QLabel(""); self.lbl_bins.setWordWrap(True); self.lbl_notes = QLabel(""); self.lbl_notes.setWordWrap(True); summary_layout.addWidget(summary_title); summary_layout.addWidget(self.lbl_summary); summary_layout.addWidget(self.lbl_bins); summary_layout.addWidget(self.lbl_notes)
        explain_container_layout.addWidget(self.summary_box); self.explain_scroll.setWidget(self.explain_container); layout.addWidget(self.explain_scroll, stretch=1)
        btn_row = QHBoxLayout(); btn_row.addStretch(1); self.btn_close = QPushButton("Kembali"); self.btn_close.setObjectName("Secondary"); btn_row.addWidget(self.btn_close); layout.addLayout(btn_row)
        self.btn_close.clicked.connect(self.accept)

    def _render_graph_coloring(self):
        try:
            gal_cap = 4; kar_cap = 2
            self.G = build_order_graph_from_json(self.orders_simple, galon_cap=gal_cap, kardus_cap=kar_cap)
            self.coloring, bins = color_graph_with_capacity(self.G, galon_cap=gal_cap, kardus_cap=kar_cap)
            self.bins = bins
            self.ax.clear()
            pos = nx.spring_layout(self.G, seed=42)
            max_color = max(self.coloring.values()) if self.coloring else 0
            palette = plt.get_cmap('tab20', max(1, max_color + 1))
            node_colors = [palette(self.coloring.get(n, 0)) for n in self.G.nodes()]
            nx.draw(self.G, pos=pos, with_labels=False, node_size=500, node_color=node_colors, ax=self.ax)
            labels = {n: self.name_map.get(str(n), str(n)) for n in self.G.nodes()}
            nx.draw_networkx_labels(self.G, pos, labels=labels, font_size=9, ax=self.ax)
            self.ax.set_title("Delivery Conflict Graph (Graph Coloring)")
            self.fig.tight_layout()
            self.canvas.draw()
            if self.bins:
                bins_lines = []
                for cid in sorted(self.bins.keys()):
                    nodes = self.bins[cid]['nodes']
                    tg = sum(int(self.G.nodes[n].get('galon', 0)) for n in nodes)
                    tk = sum(int(self.G.nodes[n].get('kardus', 0)) for n in nodes)
                    names = [self.name_map.get(str(n), str(n)) for n in nodes]
                    bins_lines.append(f"  • Pengiriman {cid+1}: {names}  (total galon={tg}/{gal_cap}, kardus={tk}/{kar_cap})")
                self.lbl_summary.setText(f"Jumlah warna (pengiriman): {len(self.bins)}")
                self.lbl_bins.setText("\n".join(bins_lines))
            else:
                self.lbl_summary.setText("Jumlah warna (pengiriman): 0")
                self.lbl_bins.setText("Belum ada rekomendasi kelompok pengiriman.")
        except Exception as e:
            err = f"Gagal merender graph coloring: {e}"
            try: self.lbl_summary.setText(err); self.lbl_bins.setText(""); self.lbl_notes.setText("")
            except Exception: pass
