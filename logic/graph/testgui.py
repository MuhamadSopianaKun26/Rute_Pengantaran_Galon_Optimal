import sys, os, json, hashlib
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QFileDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QObject, pyqtSlot
from PyQt5.QtWebChannel import QWebChannel

import re, json
from PyQt5.QtCore import QObject, pyqtSlot

class GraphHandler(QObject):
    @pyqtSlot(str)
    def saveGraphHTML(self, graph_json_str):
        """
        graph_json_str: JSON string dari frontend berisi list editedMarkers
        Format tiap node: {"idx": <idx>, "lat": <lat>, "lng": <lng>, "nama": <nama>, "id": <id>}
        """
        data = json.loads(graph_json_str)
        print(data)
        processed_data = []

        for node in data:
            if isinstance(node, str):
                try:
                    node = json.loads(node)
                except json.JSONDecodeError:
                    continue
            processed_data.append(node)

        for node in processed_data:
            idx = node.get("idx")
            if idx is None:
                continue

        with open("./road_map_detailed.html", "r", encoding="utf-8") as f:
            html = f.read()

        for node in data:
            idx = node.get("idx")
            if idx is None:
                continue  # skip jika idx tidak ada

            marker_hash = hashlib.md5(str(idx).encode()).hexdigest()
            marker_var = f"circle_marker_{marker_hash}"

            nama = node.get("nama", "Nama Tidak Ada")
            node_id = node.get("id", "ID Tidak Ada")

            # tooltip baru
            new_tooltip = (
                f"`<div>\n"
                f"     <b>{nama}</b><br>ID: {node_id}\n"
                f" </div>`"
            )

            # regex: cari bindTooltip untuk marker tertentu
            pattern = re.compile(
                rf"({marker_var}\.bindTooltip\()\s*`[\s\S]*?`(\s*,\s*\{{\s*\"sticky\":\s*true\s*,?\s*\}}\s*\)\s*;)",
                re.MULTILINE
            )

            new_html, count = re.subn(pattern, rf"\1{new_tooltip}\2", html)

            if count > 0:
                html = new_html
                print(f"✅ Tooltip pada {marker_var} diperbarui.")
            else:
                print(f"⚠️ {marker_var} tidak ditemukan, dilewati.")

        with open("./road_map_detailed.html", "w", encoding="utf-8") as f:
            f.write(html)

        print("💾 Semua tooltip pada circle_marker diperbarui.")


class Backend(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    @pyqtSlot(str)
    def saveGeoJSON(self, geojson_str):
        with open("./intersections_area.geojson", "w", encoding="utf-8") as f:
            f.write(geojson_str)
        print("✅ GeoJSON berhasil disimpan.")

    

class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GUI Peta dengan Analisis Graf")
        self.setGeometry(100, 100, 1200, 800)
        filename = "./road_map_detailed.html"

        # Layout utama
        main_layout = QHBoxLayout()

        # Sidebar tombol
        button_layout = QVBoxLayout()
        btn_rute_tercepat = QPushButton("Cari Rute Tercepat")
        btn_cut_vertex = QPushButton("Tampilkan Cut Vertex")
        btn_cut_edge = QPushButton("Tampilkan Cut Edge")
        btn_tambah_node = QPushButton("Tambah Node")
        btn_export_geojson = QPushButton("Ekspor GeoJSON")
        btn_save_graf = QPushButton("Save Graf")


        btn_rute_tercepat.clicked.connect(self.cari_rute_tercepat)
        btn_cut_vertex.clicked.connect(self.tampilkan_cut_vertex)
        btn_cut_edge.clicked.connect(self.tampilkan_cut_edge)
        btn_tambah_node.clicked.connect(self.tambah_node)
        btn_export_geojson.clicked.connect(self.ekspor_geojson)
        btn_save_graf.clicked.connect(self.save_graph)

        button_layout.addWidget(btn_rute_tercepat)
        button_layout.addWidget(btn_cut_vertex)
        button_layout.addWidget(btn_cut_edge)
        button_layout.addWidget(btn_tambah_node)
        button_layout.addWidget(btn_export_geojson)
        button_layout.addWidget(btn_save_graf)
        button_layout.addStretch()

        # Web view untuk menampilkan peta
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl.fromLocalFile(os.path.abspath(filename)))

        # Gabungkan layout tombol dan peta
        main_layout.addLayout(button_layout, 1)
        main_layout.addWidget(self.web_view, 4)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.backend = Backend()
        self.channel = QWebChannel()
        self.graph_handler = GraphHandler()
        self.channel.registerObject("geoBackend", self.backend)
        self.channel.registerObject("graphHandler", self.graph_handler)
        self.web_view.page().setWebChannel(self.channel)
        self.web_view.loadFinished.connect(self.on_load_finished)

    def on_load_finished(self):
        print("Halaman sudah dimuat dan siap")

    def cari_rute_tercepat(self):
        self.web_view.page().runJavaScript("alert('Fungsi Rute Tercepat belum diimplementasikan');")

    def tampilkan_cut_vertex(self):
        self.web_view.page().runJavaScript("alert('Fungsi Cut Vertex belum diimplementasikan');")

    def tampilkan_cut_edge(self):
        self.web_view.page().runJavaScript("alert('Fungsi Cut Edge belum diimplementasikan');")

    def tambah_node(self):
        self.web_view.page().runJavaScript("tambahNode();")
    
    def ekspor_geojson(self):
        self.web_view.page().runJavaScript("console.log('Jumlah marker:', markerList.length)")
        self.web_view.page().runJavaScript("exportGeoJSON();")
    
    def save_graph(self):
        self.web_view.page().runJavaScript("exportGraphHTML();")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MapWindow()
    window.show()
    sys.exit(app.exec_())
