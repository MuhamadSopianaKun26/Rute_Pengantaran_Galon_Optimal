import sys
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QFrame, QStackedWidget, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QLinearGradient

# Import auth logic
try:
    from logic.file.auth_logic import login_user
except ImportError:
    # Fallback jika import gagal
    def login_user(email, password):
        return True, "Login berhasil (mode demo)", {"name": "Demo User", "email": email, "role": "customer"}

class RoleButton(QPushButton):
    """Custom button untuk pemilihan role dengan animasi dan styling"""
    
    def __init__(self, title, description, icon_text, parent=None):
        super().__init__(parent)
        self.title = title
        self.description = description
        self.icon_text = icon_text
        self.is_selected = False
        
        self.setFixedSize(320, 130)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Setup layout internal
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)
        
        # Icon label
        self.icon_label = QLabel(icon_text)
        self.icon_label.setFixedSize(50, 50)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                color: #4A90A4;
                background: transparent;
                border-radius: 25px;
                border: 2px solid #4A90A4;
            }
        """)
        
        # Text container
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(5)
        
        # Title label
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #2C5F6F; background: transparent;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Description label
        self.desc_label = QLabel(description)
        self.desc_label.setFont(QFont("Segoe UI", 10))
        self.desc_label.setStyleSheet("color: #5A8A9B; background: transparent;")
        self.desc_label.setWordWrap(True)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        text_layout.addStretch()
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.desc_label)
        text_layout.addStretch()
        
        layout.addWidget(self.icon_label)
        layout.addWidget(text_container)
        
        self.update_style()
    
    def update_style(self):
        """Update style berdasarkan state"""
        if self.is_selected:
            style = """
                RoleButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(74, 144, 164, 0.15),
                        stop:1 rgba(106, 190, 205, 0.15));
                    border: 2px solid #4A90A4;
                    border-radius: 15px;
                }
                RoleButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(74, 144, 164, 0.25),
                        stop:1 rgba(106, 190, 205, 0.25));
                }
            """
        else:
            style = """
                RoleButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(240, 248, 250, 0.8),
                        stop:1 rgba(230, 245, 248, 0.8));
                    border: 1px solid rgba(74, 144, 164, 0.3);
                    border-radius: 15px;
                }
                RoleButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(74, 144, 164, 0.1),
                        stop:1 rgba(106, 190, 205, 0.1));
                    border: 2px solid rgba(74, 144, 164, 0.5);
                }
            """
        self.setStyleSheet(style)
    
    def set_selected(self, selected):
        """Set status selected"""
        self.is_selected = selected
        self.update_style()


class StyledLineEdit(QLineEdit):
    """Custom QLineEdit dengan styling tema air"""
    
    def __init__(self, placeholder_text, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder_text)
        self.setFixedHeight(50)
        self.setFont(QFont("Segoe UI", 12))
        
        self.setStyleSheet("""
            StyledLineEdit {
                background-color: rgba(240, 248, 250, 0.9);
                border: 2px solid rgba(74, 144, 164, 0.3);
                border-radius: 10px;
                padding: 0 15px;
                color: #2C5F6F;
                letter-spacing: 1px;
            }
            StyledLineEdit:focus {
                border: 2px solid #4A90A4;
                background-color: rgba(255, 255, 255, 0.95);
            }
            StyledLineEdit::placeholder {
                color: rgba(74, 144, 164, 0.6);
                letter-spacing: 0.5px;
            }
        """)


class StyledButton(QPushButton):
    """Custom QPushButton dengan styling tema air"""
    
    def __init__(self, text, button_type="primary", parent=None):
        super().__init__(text, parent)
        self.button_type = button_type
        self.setFixedHeight(45)
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if button_type == "primary":
            self.setStyleSheet("""
                StyledButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #4A90A4, stop:1 #6ABECD);
                    color: white;
                    border: none;
                    border-radius: 10px;
                    font-weight: bold;
                }
                StyledButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #3A7A8A, stop:1 #5AAEBD);
                }
                StyledButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #2A6A7A, stop:1 #4A9EAD);
                }
            """)
        elif button_type == "secondary":
            self.setStyleSheet("""
                StyledButton {
                    background: rgba(240, 248, 250, 0.9);
                    color: #4A90A4;
                    border: 2px solid #4A90A4;
                    border-radius: 10px;
                    font-weight: bold;
                }
                StyledButton:hover {
                    background: rgba(74, 144, 164, 0.1);
                    color: #3A7A8A;
                }
                StyledButton:pressed {
                    background: rgba(74, 144, 164, 0.2);
                }
            """)


class LoginPage(QMainWindow):
    """Halaman login utama dengan tema air dan transisi smooth"""
    
    # Signals
    login_success = pyqtSignal(str, dict)  # role, user_data
    open_signup = pyqtSignal()
    window_closed = pyqtSignal()  # Signal ketika window ditutup secara manual
    
    def __init__(self):
        super().__init__()
        self.selected_role = None
        self.is_closing_programmatically = False
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI components"""
        self.setWindowTitle("AquaGalon - Login")
        self.setFixedSize(1200, 800)
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #E6F7FA, stop:0.5 #B2EBF2, stop:1 #80DEEA);
            }
        """)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left panel (decorative)
        self.create_left_panel(main_layout)
        
        # Right panel (main content)
        self.create_right_panel(main_layout)
        
    def create_left_panel(self, parent_layout):
        """Buat panel kiri untuk hiasan dan logo"""
        left_panel = QFrame()
        left_panel.setFixedWidth(600)
        left_panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(74, 144, 164, 0.8),
                    stop:1 rgba(106, 190, 205, 0.6));
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
            }
        """)
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.setSpacing(30)
        
        # Logo/Icon
        logo_label = QLabel("🌊")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("""
            QLabel {
                font-size: 120px;
                color: white;
                background: transparent;
                border-radius: 80px;
                padding: 40px;
            }
        """)
        logo_label.setFixedSize(160, 160)
        
        # Title
        title_label = QLabel("AquaGalon")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white; background: transparent;")
        
        # Subtitle
        subtitle_label = QLabel("Sistem Pemesanan & Pengiriman Galon\nBerbasis Graph Theory")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setFont(QFont("Segoe UI", 14))
        subtitle_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); background: transparent;")
        subtitle_label.setWordWrap(True)
        
        left_layout.addStretch()
        left_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(subtitle_label, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addStretch()
        
        parent_layout.addWidget(left_panel)
        
    def create_right_panel(self, parent_layout):
        """Buat panel kanan untuk konten utama"""
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.95);
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
            }
        """)
        
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(60, 80, 60, 80)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Stacked widget untuk transisi
        self.stacked_widget = QStackedWidget()
        
        # Page 1: Role Selection
        self.create_role_selection_page()
        
        # Page 2: Login Form
        self.create_login_form_page()
        
        right_layout.addWidget(self.stacked_widget)
        parent_layout.addWidget(right_panel)
        
    def create_role_selection_page(self):
        """Buat halaman pemilihan role"""
        role_page = QWidget()
        role_layout = QVBoxLayout(role_page)
        role_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        role_layout.setSpacing(30)
        
        # Title
        title = QLabel("Pilih Peran Anda")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #2C5F6F; margin-bottom: 20px;")
        
        # Role buttons container
        buttons_container = QWidget()
        buttons_layout = QVBoxLayout(buttons_container)
        buttons_layout.setSpacing(20)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Customer button
        self.customer_btn = RoleButton(
            "Pembeli", 
            "Pesan galon dan produk lainnya", 
            "👤"
        )
        self.customer_btn.clicked.connect(lambda: self.select_role("customer"))
        
        # Seller button
        self.seller_btn = RoleButton(
            "Penjual", 
            "Kelola pesanan dan pengiriman", 
            "🚚"
        )
        self.seller_btn.clicked.connect(lambda: self.select_role("seller"))
        
        buttons_layout.addWidget(self.customer_btn)
        buttons_layout.addWidget(self.seller_btn)
        
        # Continue button
        self.continue_btn = StyledButton("Lanjutkan", "primary")
        self.continue_btn.setFixedWidth(250)
        self.continue_btn.setFixedHeight(50)
        self.continue_btn.clicked.connect(self.show_login_form)
        self.continue_btn.setEnabled(False)
        
        role_layout.addWidget(title)
        role_layout.addWidget(buttons_container)
        role_layout.addSpacing(30)
        role_layout.addWidget(self.continue_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.stacked_widget.addWidget(role_page)
        
    def create_login_form_page(self):
        """Buat halaman form login"""
        login_page = QWidget()
        login_layout = QVBoxLayout(login_page)
        login_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        login_layout.setSpacing(20)
        
        # Title
        self.login_title = QLabel("Masuk sebagai Pembeli")
        self.login_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.login_title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.login_title.setStyleSheet("color: #2C5F6F; margin-bottom: 20px;")
        
        # Form container
        form_container = QWidget()
        form_container.setFixedWidth(400)
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(15)
        
        # Email input
        self.email_input = StyledLineEdit("Masukkan email")
        self.email_input.textChanged.connect(self.validate_realtime)
        
        # Password input
        self.password_input = StyledLineEdit("Masukkan sandi")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.textChanged.connect(self.validate_realtime)
        
        # Error message label
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("""
            QLabel {
                color: #E74C3C;
                font-size: 12px;
                background-color: rgba(231, 76, 60, 0.1);
                border: 1px solid rgba(231, 76, 60, 0.3);
                border-radius: 5px;
                padding: 8px;
            }
        """)
        self.error_label.hide()
        
        form_layout.addWidget(self.email_input)
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(self.error_label)
        
        # Buttons container
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(15)
        
        # Login button
        self.login_btn = StyledButton("Masuk", "primary")
        self.login_btn.setFixedWidth(120)
        self.login_btn.setFixedHeight(50)
        self.login_btn.clicked.connect(self.attempt_login)
        
        buttons_layout.addWidget(self.login_btn)
        
        # Signup link
        signup_container = QWidget()
        signup_layout = QHBoxLayout(signup_container)
        signup_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        signup_layout.setSpacing(5)
        
        signup_text = QLabel("Belum memiliki akun?")
        signup_text.setStyleSheet("color: #5A8A9B; font-size: 12px;")
        
        self.signup_link = QLabel("Buat akun")
        self.signup_link.setStyleSheet("""
            QLabel {
                color: #4A90A4;
                font-size: 12px;
                font-weight: bold;
                text-decoration: underline;
            }
            QLabel:hover {
                color: #3A7A8A;
            }
        """)
        self.signup_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.signup_link.mousePressEvent = lambda e: self.open_signup.emit()
        
        signup_layout.addWidget(signup_text)
        signup_layout.addWidget(self.signup_link)
        
        # Back button
        back_btn = QPushButton("← Kembali")
        back_btn.setFixedSize(80, 30)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(74, 144, 164, 0.1);
                border: 1px solid #4A90A4;
                border-radius: 6px;
                color: #4A90A4;
                font-size: 11px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgba(74, 144, 164, 0.2);
                color: #3A7A8A;
            }
            QPushButton:pressed {
                background-color: rgba(74, 144, 164, 0.3);
            }
        """)
        back_btn.clicked.connect(self.show_role_selection)
        
        login_layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        login_layout.addSpacing(10)
        login_layout.addWidget(self.login_title)
        login_layout.addWidget(form_container, alignment=Qt.AlignmentFlag.AlignCenter)
        login_layout.addSpacing(20)
        login_layout.addWidget(buttons_container, alignment=Qt.AlignmentFlag.AlignCenter)
        login_layout.addSpacing(15)
        login_layout.addWidget(signup_container, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.stacked_widget.addWidget(login_page)
        
    def select_role(self, role):
        """Handle pemilihan role"""
        self.selected_role = role
        
        # Update button states
        self.customer_btn.set_selected(role == "customer")
        self.seller_btn.set_selected(role == "seller")
        
        # Enable continue button
        self.continue_btn.setEnabled(True)
        
    def show_login_form(self):
        """Tampilkan form login"""
        if not self.selected_role:
            return
            
        # Update title berdasarkan role
        if self.selected_role == "customer":
            self.login_title.setText("Masuk sebagai Pembeli")
        else:
            self.login_title.setText("Masuk sebagai Penjual")
            
        # Switch ke halaman login
        self.stacked_widget.setCurrentIndex(1)
        
    def show_role_selection(self):
        """Kembali ke halaman pemilihan role"""
        self.stacked_widget.setCurrentIndex(0)
        self.clear_form()
        
    def clear_form(self):
        """Bersihkan form input"""
        self.email_input.clear()
        self.password_input.clear()
        self.error_label.hide()
        
    def show_error(self, message):
        """Tampilkan pesan error"""
        self.error_label.setText(message)
        self.error_label.show()
        
    def validate_email_login(self, email):
        """Validasi email untuk login (lebih sederhana dari signup)"""
        if not email or len(email.strip()) == 0:
            return "Email harus diisi!"
            
        email = email.strip().lower()
        
        # Basic email validation
        if '@' not in email:
            return "Format email tidak valid! Harus mengandung @"
            
        if '.' not in email.split('@')[1]:
            return "Format email tidak valid! Domain harus mengandung titik"
            
        # Regex pattern untuk email yang valid
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return "Format email tidak valid! Contoh: nama@domain.com"
            
        return None
    
    def validate_password_login(self, password):
        """Validasi password untuk login"""
        if not password:
            return "Sandi harus diisi!"
            
        if len(password) < 6:
            return "Sandi minimal 6 karakter!"
            
        return None
    
    def validate_realtime(self):
        """Validasi real-time saat user mengetik"""
        # Reset error message
        self.error_label.hide()
        
        email = self.email_input.text()
        password = self.password_input.text()
        
        # Validasi email jika sedang difokuskan
        if self.email_input.hasFocus() and email:
            error = self.validate_email_login(email)
            if error:
                self.show_error(error)
                return
                
        # Validasi password jika sedang difokuskan
        if self.password_input.hasFocus() and password:
            error = self.validate_password_login(password)
            if error:
                self.show_error(error)
                return
    
    def validate_login_form(self):
        """Validasi lengkap form login sebelum submit"""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        # Validasi email
        error = self.validate_email_login(email)
        if error:
            self.show_error(error)
            self.email_input.setFocus()
            return False
            
        # Validasi password
        error = self.validate_password_login(password)
        if error:
            self.show_error(error)
            self.password_input.setFocus()
            return False
            
        return True
    
    def attempt_login(self):
        """Coba login dengan kredensial"""
        # Clear previous errors
        self.error_label.hide()
        
        # Validasi form
        if not self.validate_login_form():
            return
            
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        # Gunakan auth_logic untuk login
        try:
            success, message, user_data = login_user(email, password)
            
            if success and user_data:
                # Cek apakah role sesuai dengan yang dipilih
                if user_data["role"] != self.selected_role:
                    self.show_error(f"Akun ini terdaftar sebagai {user_data['role']}, bukan {self.selected_role}. Silakan pilih role yang sesuai.")
                    return
                
                self.is_closing_programmatically = True  # Set flag sebelum emit signal
                self.login_success.emit(self.selected_role, user_data)
            else:
                self.show_error(message)
                
        except Exception as e:
            self.show_error(f"Error saat login: {str(e)}")
            

    
    def close_programmatically(self):
        """Tutup window secara programmatic tanpa konfirmasi"""
        self.is_closing_programmatically = True
        self.close()
    
    def closeEvent(self, event):
        """Handle ketika window akan ditutup"""
        if self.is_closing_programmatically:
            # Tutup tanpa konfirmasi jika dipanggil secara programmatic
            event.accept()
        else:
            # Tampilkan konfirmasi hanya jika user menutup window secara manual
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, 
                'Konfirmasi',
                'Apakah Anda yakin ingin keluar dari aplikasi?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.window_closed.emit()
                event.accept()
            else:
                event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = LoginPage()
    window.show()
    
    sys.exit(app.exec())