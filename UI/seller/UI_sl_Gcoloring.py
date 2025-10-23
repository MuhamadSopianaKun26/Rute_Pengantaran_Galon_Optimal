from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QComboBox, QScrollArea, QWidget, QSizePolicy
)
import os, json
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from logic.graph.graph_coloring import build_order_graph_from_json, color_graph_with_capacity


def _db_path(filename: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, 'Database', filename)


class OrderPreviewDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
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
            """
        )
        self._build_ui()
        try:
            self.cmb_schedule.currentTextChanged.connect(self._load_and_render_orders)
        except Exception:
            pass
        self._load_and_render_orders()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Preview Orderan")
        title.setObjectName("Title")
        layout.addWidget(title)

        schedule_row = QHBoxLayout()
        schedule_row.setSpacing(8)
        lbl = QLabel("Jadwal:")
        lbl.setStyleSheet("color:#2C5F6F;font-weight:700;")
        self.cmb_schedule = QComboBox()
        self.cmb_schedule.addItems(["segera", "09.00", "12.00", "15.00", "18.00"])
        self.cmb_schedule.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        schedule_row.addWidget(lbl)
        schedule_row.addWidget(self.cmb_schedule)
        schedule_row.addStretch(1)
        layout.addLayout(schedule_row)

        self.map_box = QFrame()
        self.map_box.setObjectName("MapBox")
        map_layout = QVBoxLayout(self.map_box)
        map_layout.setContentsMargins(16, 16, 16, 16)
        map_layout.setSpacing(10)
        map_title = QLabel("Daftar Pesanan (sesuai jadwal)")
        map_title.setObjectName("SectionTitle")
        map_layout.addWidget(map_title)

        self.orders_scroll = QScrollArea()
        self.orders_scroll.setWidgetResizable(True)
        self.orders_container = QWidget()
        self.orders_layout = QVBoxLayout(self.orders_container)
        self.orders_layout.setContentsMargins(0, 0, 0, 0)
        self.orders_layout.setSpacing(6)
        self.lbl_orders = QLabel("Belum ada data. Pilih jadwal untuk menampilkan daftar.")
        self.lbl_orders.setWordWrap(True)
        self.orders_layout.addWidget(self.lbl_orders)
        self.orders_layout.addStretch(1)
        self.orders_scroll.setWidget(self.orders_container)
        map_layout.addWidget(self.orders_scroll)

        # Jadikan area map_box statis (lebih panjang ke bawah)
        self.map_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.map_box.setFixedHeight(420)
        layout.addWidget(self.map_box, stretch=0)

        self.opt_box = QFrame()
        self.opt_box.setObjectName("InfoBox")
        opt_layout = QVBoxLayout(self.opt_box)
        opt_layout.setContentsMargins(16, 16, 16, 16)
        opt_layout.setSpacing(8)
        opt_title = QLabel("Urutan Pengiriman Optimal")
        opt_title.setObjectName("SectionTitle")
        self.lbl_optimal = QLabel("Menunggu graph coloring.....")
        self.lbl_optimal.setWordWrap(True)
        opt_layout.addWidget(opt_title)
        opt_layout.addWidget(self.lbl_optimal)
        layout.addWidget(self.opt_box, stretch=2)

        btn_row = QHBoxLayout()
        self.btn_do_gc = QPushButton("Lakukan Graph Coloring")
        self.btn_do_gc.setObjectName("Primary")
        btn_row.addWidget(self.btn_do_gc)
        btn_row.addStretch(1)
        self.btn_back = QPushButton("Kembali")
        self.btn_back.setObjectName("Secondary")
        btn_row.addWidget(self.btn_back)
        layout.addLayout(btn_row)

        self.btn_back.clicked.connect(self.reject)
        self.btn_do_gc.clicked.connect(self._open_gc_preview)

    def _normalize_schedule(self, s: str) -> str:
        s = (s or '').strip().lower()
        s = s.replace(':', '.')
        return s

    def _load_and_render_orders(self):
        path = _db_path('order_data.json')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f) or []
        except Exception:
            data = []

        selected = self._normalize_schedule(self.cmb_schedule.currentText())

        lines = []
        for order in data:
            status = (order.get('status') or '').strip().lower()
            if status != 'sedang_disiapkan':
                continue
            sch = self._normalize_schedule(str(order.get('schedule', '')))
            if sch != selected:
                continue

            name = order.get('customer_name') or '-'
            street = order.get('street') or ''
            area = order.get('area') or ''
            dest = street if street else (area or '-')

            items = order.get('items') or []
            parts = []
            for it in items:
                nm = str(it.get('name', 'Item'))
                qty = it.get('qty', 0)
                parts.append(f"{nm} : {qty}")

            lines.append(f"{name} - {dest}")
            lines.append(f"[ {', '.join(parts)} ]")
            lines.append("")

        text = "\n".join(lines).strip()
        if not text:
            text = "Tidak ada pesanan untuk jadwal ini."
        self.lbl_orders.setText(text)

    def _open_gc_preview(self):
        orders_simple = self._collect_filtered_orders()
        dlg = GraphColoringPreview(orders_simple, self)
        dlg.exec()
        try:
            bins = getattr(dlg, 'bins', {}) or {}
            if not bins:
                self.lbl_optimal.setText("Belum ada hasil graph coloring untuk jadwal ini.")
                return
            # Build quick lookup maps
            name_map = {str(o.get('id')): str(o.get('name') or o.get('id')) for o in orders_simple}
            gal_map = {str(o.get('id')): int(o.get('galon', 0)) for o in orders_simple}
            box_map = {str(o.get('id')): int(o.get('kardus', 0)) for o in orders_simple}

            lines = []
            lines.append(f"Jumlah opsi pengiriman: {len(bins)}")
            for cid in sorted(bins.keys()):
                nodes = bins[cid].get('nodes', [])
                names = [name_map.get(str(n), str(n)) for n in nodes]
                total_g = sum(gal_map.get(str(n), 0) for n in nodes)
                total_k = sum(box_map.get(str(n), 0) for n in nodes)
                lines.append(f"- Pengiriman {cid+1}: {names}  (galon={total_g}, kardus={total_k})")
            self.lbl_optimal.setText("\n".join(lines))
        except Exception:
            # Keep silent if any error; leave previous text
            pass

    def _collect_filtered_orders(self):
        path = _db_path('order_data.json')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f) or []
        except Exception:
            data = []

        selected = self._normalize_schedule(self.cmb_schedule.currentText())
        result = []
        counter = 1
        for order in data:
            status = (order.get('status') or '').strip().lower()
            if status != 'sedang_disiapkan':
                continue
            sch = self._normalize_schedule(str(order.get('schedule', '')))
            if sch != selected:
                continue
            oid = str(order.get('id') or order.get('order_id') or order.get('customer_name') or counter)
            name = order.get('customer_name') or oid
            counter += 1
            galon_qty = 0
            kardus_qty = 0
            for it in (order.get('items') or []):
                nm = str(it.get('name', '')).lower()
                qty = int(it.get('qty', 0) or 0)
                if 'galon' in nm:
                    galon_qty += qty
                if 'box' in nm or 'kardus' in nm:
                    kardus_qty += qty
            result.append({
                'id': oid,
                'galon': galon_qty,
                'kardus': kardus_qty,
                'name': name,
            })
        return result


class GraphColoringPreview(QDialog):
    def __init__(self, orders_simple: list, parent=None):
        super().__init__(parent)
        self.orders_simple = orders_simple or []
        # map id -> display name (customer name)
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

        title = QLabel("Hasil Graph Coloring")
        title.setObjectName("Title")
        layout.addWidget(title)

        self.canvas_box = QFrame()
        self.canvas_box.setObjectName("CanvasBox")
        canvas_layout = QVBoxLayout(self.canvas_box)
        canvas_layout.setContentsMargins(16, 16, 16, 16)
        canvas_layout.setSpacing(8)
        self.fig, self.ax = plt.subplots(figsize=(16, 12))
        self.canvas = FigureCanvas(self.fig)
        # Wrap canvas in a scroll area to handle overflow
        self.graph_scroll = QScrollArea()
        self.graph_scroll.setWidgetResizable(True)
        self.graph_container = QWidget()
        self.graph_container_layout = QVBoxLayout(self.graph_container)
        self.graph_container_layout.setContentsMargins(0, 0, 0, 0)
        self.graph_container_layout.addWidget(self.canvas)
        self.graph_scroll.setWidget(self.graph_container)
        canvas_layout.addWidget(self.graph_scroll)
        layout.addWidget(self.canvas_box, stretch=5)

        # Explanation area (single right-side style) wrapped in a scroll area
        self.explain_scroll = QScrollArea()
        self.explain_scroll.setWidgetResizable(True)
        self.explain_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.explain_container = QWidget()
        explain_container_layout = QVBoxLayout(self.explain_container)
        explain_container_layout.setContentsMargins(0, 0, 0, 0)
        explain_container_layout.setSpacing(12)

        # Summary and notes box (acts as the right-side explanation)
        self.summary_box = QFrame()
        self.summary_box.setObjectName("InfoBox")
        summary_layout = QVBoxLayout(self.summary_box)
        summary_layout.setContentsMargins(16, 16, 16, 16)
        summary_layout.setSpacing(8)
        summary_title = QLabel("Ringkasan Coloring")
        summary_title.setObjectName("SectionTitle")
        self.lbl_summary = QLabel("")  # jumlah warna
        self.lbl_summary.setWordWrap(True)
        self.lbl_bins = QLabel("")     # isi tiap warna
        self.lbl_bins.setWordWrap(True)
        self.lbl_notes = QLabel("")    # penjelasan
        self.lbl_notes.setWordWrap(True)
        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(self.lbl_summary)
        summary_layout.addWidget(self.lbl_bins)
        summary_layout.addWidget(self.lbl_notes)

        explain_container_layout.addWidget(self.summary_box)
        self.explain_scroll.setWidget(self.explain_container)
        layout.addWidget(self.explain_scroll, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_close = QPushButton("Kembali")
        self.btn_close.setObjectName("Secondary")
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

        self.btn_close.clicked.connect(self.accept)

    def _render_graph_coloring(self):
        try:
            # Kapasitas sesuai penjelasan
            gal_cap = 4
            kar_cap = 2
            # Bangun graf dan pewarnaan
            self.G = build_order_graph_from_json(self.orders_simple, galon_cap=gal_cap, kardus_cap=kar_cap)
            self.coloring, bins = color_graph_with_capacity(self.G, galon_cap=gal_cap, kardus_cap=kar_cap)
            self.bins = bins

            # Gambar graf berwarna
            self.ax.clear()
            pos = nx.spring_layout(self.G, seed=42)
            # Map node colors
            max_color = max(self.coloring.values()) if self.coloring else 0
            palette = plt.get_cmap('tab20', max(1, max_color + 1))
            node_colors = [palette(self.coloring.get(n, 0)) for n in self.G.nodes()]
            nx.draw(self.G, pos=pos, with_labels=False, node_size=500, node_color=node_colors, ax=self.ax)
            # draw custom labels using customer names
            labels = {n: self.name_map.get(str(n), str(n)) for n in self.G.nodes()}
            nx.draw_networkx_labels(self.G, pos, labels=labels, font_size=9, ax=self.ax)
            self.ax.set_title("Delivery Conflict Graph (Graph Coloring)")
            self.fig.tight_layout()
            self.canvas.draw()

            # Ringkasan bins (pengiriman)
            if self.bins:
                bins_lines = []
                for cid in sorted(self.bins.keys()):
                    nodes = self.bins[cid]['nodes']
                    tg = sum(int(self.G.nodes[n].get('galon', 0)) for n in nodes)
                    tk = sum(int(self.G.nodes[n].get('kardus', 0)) for n in nodes)
                    names = [self.name_map.get(str(n), str(n)) for n in nodes]
                    bins_lines.append(f"  • Pengiriman {cid+1}: {names}  (total galon={tg}/4, kardus={tk}/2)")
                self.lbl_summary.setText(f"Jumlah warna (pengiriman): {len(self.bins)}")
                self.lbl_bins.setText("\n".join(bins_lines))
            else:
                self.lbl_summary.setText("Jumlah warna (pengiriman): 0")
                self.lbl_bins.setText("Belum ada rekomendasi kelompok pengiriman.")

        except Exception as e:
            err = f"Gagal merender graph coloring: {e}"
            try:
                self.lbl_summary.setText(err)
                self.lbl_bins.setText("")
                self.lbl_notes.setText("")
            except Exception:
                pass
