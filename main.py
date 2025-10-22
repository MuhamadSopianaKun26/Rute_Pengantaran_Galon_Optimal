"""
AquaGalon - Sistem Pemesanan & Pengiriman Galon
Berbasis Graph Theory untuk Matematika Diskrit

Main entry point untuk aplikasi
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon

# Add UI path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'UI'))

# Import components
from UI.login.UI_login import create_login_system
from graph_algorithms import create_graph_system


class AppController(QMainWindow):
    """
    Main application controller
    Mengelola alur aplikasi dari login hingga main interface
    """
    
    def __init__(self):
        super().__init__()
        self.current_user = None
        self.current_role = None
        self.login_system = None
        self.graph_system = None
        self.graph_visualizer = None
        
        self.init_app()
        
    def init_app(self):
        """Initialize aplikasi"""
        self.setWindowTitle("AquaGalon - Sistem Pemesanan & Pengiriman")
        self.setMinimumSize(1200, 800)
        
        # Set application icon (jika ada)
        # self.setWindowIcon(QIcon("assets/icon.png"))
        
        # Initialize graph system
        self.graph_system, self.graph_visualizer = create_graph_system()
        
        # Show splash screen atau langsung ke login
        self.show_login()
        
    def show_login(self):
        """Tampilkan halaman login"""
        self.login_system = create_login_system()
        
        # Connect signals
        self.login_system.login_successful.connect(self.on_login_success)
        self.login_system.login_cancelled.connect(self.on_login_cancelled)
        
        # Hide main window dan show login
        self.hide()
        self.login_system.show_login()
        
    def on_login_success(self, role: str, user_data: dict):
        """Handle login berhasil"""
        self.current_role = role
        self.current_user = user_data or {}
        
        print(f"Login berhasil: {self.current_user.get('name')} sebagai {role}")
        
        # Show main application
        self.show_main_application()
        
    def on_login_cancelled(self):
        """Handle login dibatalkan"""
        print("Login dibatalkan, menutup aplikasi...")
        self.close()
        
    def show_main_application(self):
        """Tampilkan aplikasi utama setelah login"""
        # Cleanup login system
        if self.login_system:
            self.login_system.cleanup()
            self.login_system = None
        
        # Show main window
        self.show()
        self.showMaximized()  # atau self.showFullScreen()
        
        # Setup main interface berdasarkan role
        if self.current_role == "customer":
            self.setup_customer_interface()
        elif self.current_role == "seller":
            self.setup_seller_interface()
            
        # Show welcome message
        self.show_welcome_message()
        
    def setup_customer_interface(self):
        """Setup interface untuk customer"""
        print("Setting up customer interface...")
        
        try:
            # Import customer dashboard
            from UI.customer.UI_cs_main import create_customer_dashboard
            
            # Create customer dashboard
            self.customer_dashboard = create_customer_dashboard(self.current_user)
            
            # Connect signals
            self.customer_dashboard.logout_requested.connect(self.on_customer_logout)
            self.customer_dashboard.simulation_requested.connect(self.on_simulation_request)
            
            # Hide main window and show customer dashboard
            self.hide()
            self.customer_dashboard.show()
            
        except ImportError as e:
            print(f"Error importing customer dashboard: {e}")
            # Fallback ke interface sederhana
            self.setup_customer_fallback()
    
    def setup_customer_fallback(self):
        """Fallback customer interface jika dashboard gagal load"""
        from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
        
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        
        welcome_label = QLabel(f"Selamat datang, {self.current_user.get('name', 'User')}!")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        welcome_label.setStyleSheet("color: #2C5F6F; margin: 50px;")
        
        info_label = QLabel("Interface Customer sedang dalam pengembangan...")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setFont(QFont("Segoe UI", 14))
        info_label.setStyleSheet("color: #5A8A9B;")
        
        layout.addWidget(welcome_label)
        layout.addWidget(info_label)
        
        self.setCentralWidget(central_widget)
    
    def on_customer_logout(self):
        """Handle logout dari customer dashboard"""
        print("Customer logout requested")
        
        # Close customer dashboard
        if hasattr(self, 'customer_dashboard'):
            self.customer_dashboard.close()
            delattr(self, 'customer_dashboard')
        
        # Reset user data
        self.current_user = None
        self.current_role = None
        
        # Show login again
        self.show_login()
    
    def on_simulation_request(self):
        """Handle simulation request dari customer dashboard"""
        print("Simulation requested from customer dashboard")
        
        # TODO: Implementasi simulasi graph theory
        # Untuk sementara tampilkan message box
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self.customer_dashboard if hasattr(self, 'customer_dashboard') else self,
            "Simulasi",
            "Fitur simulasi graph theory akan segera hadir!\n\n"
            "Simulasi akan menampilkan:\n"
            "- Visualisasi rute pengiriman\n"
            "- Optimasi jalur terpendek\n"
            "- Analisis efisiensi pengiriman"
        )
        
    def setup_seller_interface(self):
        """Setup interface untuk seller"""
        print("Setting up seller interface...")
        try:
            from UI.seller.UI_sl_main import create_seller_dashboard
            # Buat dan tampilkan window dashboard seller
            self.seller_dashboard = create_seller_dashboard(self.current_user)
            # Sambungkan sinyal penting
            if hasattr(self.seller_dashboard, 'logout_requested'):
                self.seller_dashboard.logout_requested.connect(self.on_seller_logout)
            # Sembunyikan main window dan tampilkan dashboard seller
            self.hide()
            self.seller_dashboard.show()
        except ImportError as e:
            print(f"Error importing seller dashboard: {e}")
            # Fallback sederhana (tetap sediakan test graph)
            from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget, QPushButton
            central_widget = QWidget()
            layout = QVBoxLayout(central_widget)
            welcome_label = QLabel(f"Selamat datang, {self.current_user.get('name', 'User')}!")
            welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            welcome_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
            welcome_label.setStyleSheet("color: #2C5F6F; margin: 30px;")
            info_label = QLabel("Interface Seller - fallback")
            info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info_label.setFont(QFont("Segoe UI", 14))
            info_label.setStyleSheet("color: #5A8A9B; margin-bottom: 30px;")
            test_graph_btn = QPushButton("Test Graph Visualization")
            test_graph_btn.clicked.connect(self.test_graph_visualization)
            layout.addWidget(welcome_label)
            layout.addWidget(info_label)
            layout.addWidget(test_graph_btn, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addStretch()
            self.setCentralWidget(central_widget)
        
    def test_graph_visualization(self):
        """Test graph visualization"""
        try:
            # Get route info untuk test
            route_info = self.graph_system.get_delivery_route("Jln. Kampus Polban")
            
            # Create visualization
            canvas = self.graph_visualizer.create_route_visualization(route_info)
            
            # Show dalam dialog atau window baru
            from PyQt6.QtWidgets import QDialog, QVBoxLayout
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Graph Visualization - Rute Pengiriman")
            dialog.setMinimumSize(800, 600)
            
            layout = QVBoxLayout(dialog)
            layout.addWidget(canvas)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Gagal menampilkan graph: {str(e)}")
    
    def on_seller_logout(self):
        """Handle logout dari seller dashboard"""
        print("Seller logout requested")
        # Tutup dashboard seller
        if hasattr(self, 'seller_dashboard'):
            try:
                self.seller_dashboard.close()
            except Exception:
                pass
            delattr(self, 'seller_dashboard')
        # Reset user/role
        self.current_user = None
        self.current_role = None
        # Tampilkan login lagi
        self.show_login()
        
    def show_welcome_message(self):
        """Tampilkan pesan selamat datang"""
        role_text = {
            "customer": "Pembeli",
            "seller": "Penjual"
        }.get(self.current_role, "User")
        
        QMessageBox.information(
            self, 
            "Selamat Datang!",
            f"Selamat datang di AquaGalon, {self.current_user}!\n\n"
            f"Anda masuk sebagai: {role_text}\n"
            f"Sistem graph theory siap digunakan untuk optimasi pengiriman."
        )
        
    def closeEvent(self, event):
        """Handle ketika aplikasi ditutup"""
        # Cleanup resources tanpa konfirmasi
        # Konfirmasi sudah ditangani oleh LoginPage atau tidak perlu di main app
        if self.login_system:
            self.login_system.cleanup()
        event.accept()


def setup_application():
    """Setup aplikasi dengan konfigurasi yang diperlukan"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("AquaGalon")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Polban - Matematika Diskrit")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Set global font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Set application stylesheet (optional global styles)
    app.setStyleSheet("""
        QMainWindow {
            background-color: #F8F9FA;
        }
        QMessageBox {
            background-color: white;
            color: #2C5F6F;
        }
    """)
    
    return app


def main():
    """Main function"""
    try:
        # Setup application
        app = setup_application()
        
        # Create main controller
        controller = AppController()
        
        # Handle application exit
        def on_app_quit():
            print("AquaGalon application terminated.")
            
        app.aboutToQuit.connect(on_app_quit)
        
        # Start event loop
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()