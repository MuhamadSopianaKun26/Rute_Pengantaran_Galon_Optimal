import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWebChannel import QWebChannel

class SellerSimulation(QWidget):
    def _init_(self, parent=None):
        super()._init_(parent)
        
        # Flag untuk memastikan peta hanya di-load sekali
        self.map_loaded = False
        
        filename = os.path.abspath("logic/graph/backup.html")

        layout = QVBoxLayout(self)


        self.web_view = QWebEngineView()

        # 4. Muat URL yang sudah diformat dengan benar
        self.web_view.setUrl(QUrl.fromLocalFile(os.path.abspath(filename)))
        
        layout.addWidget(self.web_view)

        self.channel = QWebChannel()
        self.web_view.page().setWebChannel(self.channel)
        self.web_view.loadFinished.connect(self.on_load_finished)
        self.web_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
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
        
        # Ambil path file HTML asli Anda
        filename = os.path.abspath("logic/graph/road_map_detailed.html")
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

        # SEKARANG baru muat URL-nya
        self.web_view.load(QUrl.fromLocalFile(filename))
        
        # Set flag
        self.map_loaded = True

def show_simulation(self):
        """Show simulation page (keep sidebar open)"""
        # Panggil fungsi lazy load SEBELUM menampilkan halaman
        try:
            self.simulation_page.load_map_if_needed()
        except Exception as e:
            # Anda akan melihat ini jika ada error
            print(f"Gagal memanggil load_map_if_needed: {e}")

        self.content_stack.setCurrentIndex(2)
        # Sembunyikan bottom nav untuk halaman simulasi
        self.bottom_nav.hide()
        self.sidebar.set_active("simulation")
        self.update_bottom_nav_for("simulation")