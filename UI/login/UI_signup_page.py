import sys
import re
from PyQt6.QtWidgets import (QApplication, QDialog, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QFrame, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

# Import auth logic
try:
    from logic.file.auth_logic import register_user
except ImportError:
    # Fallback jika import gagal
    def register_user(name, email, password, role):
        return True, "Registrasi berhasil (mode demo)"


class StyledLineEdit(QLineEdit):
    """Custom QLineEdit dengan styling tema air untuk signup"""
    
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
    """Custom QPushButton dengan styling tema air untuk signup"""
    
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


class SignupPage(QDialog):
    """Dialog untuk registrasi akun baru dengan tema air"""
    
    # Signals
    signup_success = pyqtSignal(str, str, str)  # name, email, role
    
    def __init__(self, role="customer", parent=None):
        super().__init__(parent)
        self.role = role
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI components"""
        self.setWindowTitle("AquaGalon - Buat Akun")
        self.setFixedSize(550, 600)
        self.setModal(True)
        
        # Set background dengan tema air
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #E6F7FA, stop:0.5 #B2EBF2, stop:1 #80DEEA);
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(20)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Header section
        self.create_header(main_layout)
        
        # Form section
        self.create_form(main_layout)
        
        # Buttons section
        self.create_buttons(main_layout)
        
    def create_header(self, parent_layout):
        """Buat header dengan title saja"""
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Buat Akun Baru")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2C5F6F; background: transparent;")
        
        # Subtitle
        role_text = "Pembeli" if self.role == "customer" else "Penjual"
        subtitle_label = QLabel(f"Daftar sebagai {role_text}")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setFont(QFont("Segoe UI", 14))
        subtitle_label.setStyleSheet("color: #5A8A9B; background: transparent;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        
        parent_layout.addWidget(header_container)
        
    def create_form(self, parent_layout):
        # Form container (lebih dominan)
        form_container = QWidget()
        form_container.setFixedWidth(450)
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(18)
        
        # Name input
        self.name_input = StyledLineEdit("Masukkan nama lengkap")
        self.name_input.textChanged.connect(self.validate_realtime)
        
        # Email input
        self.email_input = StyledLineEdit("Masukkan email")
        self.email_input.textChanged.connect(self.validate_realtime)
        
        # Password input
        self.password_input = StyledLineEdit("Masukkan sandi")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.textChanged.connect(self.validate_realtime)
        
        # Confirm password input
        self.confirm_password_input = StyledLineEdit("Konfirmasi sandi")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.textChanged.connect(self.validate_realtime)
        
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
                margin: 5px 0;
            }
        """)
        self.error_label.hide()
        
        # Success message label
        self.success_label = QLabel("")
        self.success_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.success_label.setStyleSheet("""
            QLabel {
                color: #27AE60;
                font-size: 12px;
                background-color: rgba(39, 174, 96, 0.1);
                border: 1px solid rgba(39, 174, 96, 0.3);
                border-radius: 5px;
                padding: 8px;
                margin: 5px 0;
            }
        """)
        self.success_label.hide()
        
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.email_input)
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(self.confirm_password_input)
        form_layout.addWidget(self.error_label)
        form_layout.addWidget(self.success_label)
        
        parent_layout.addWidget(form_container, alignment=Qt.AlignmentFlag.AlignCenter)
        
    def create_buttons(self, parent_layout):
        """Buat tombol-tombol aksi"""
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(15)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Cancel button
        cancel_btn = StyledButton("Batal", "secondary")
        cancel_btn.setFixedWidth(120)
        cancel_btn.clicked.connect(self.reject)
        
        # Signup button
        signup_btn = StyledButton("Daftar", "primary")
        signup_btn.setFixedWidth(120)
        signup_btn.clicked.connect(self.attempt_signup)
        
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(signup_btn)
        
        parent_layout.addWidget(buttons_container)
        
        # Login link
        login_container = QWidget()
        login_layout = QHBoxLayout(login_container)
        login_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        login_layout.setSpacing(5)
        
        login_text = QLabel("Sudah memiliki akun?")
        login_text.setStyleSheet("color: #5A8A9B; font-size: 12px;")
        
        login_link = QLabel("Masuk di sini")
        login_link.setStyleSheet("""
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
        login_link.setCursor(Qt.CursorShape.PointingHandCursor)
        login_link.mousePressEvent = lambda e: self.reject()
        
        login_layout.addWidget(login_text)
        login_layout.addWidget(login_link)
        
        parent_layout.addWidget(login_container)
        
    def show_error(self, message):
        """Tampilkan pesan error"""
        self.success_label.hide()
        self.error_label.setText(message)
        self.error_label.show()
        
    def show_success(self, message):
        """Tampilkan pesan sukses"""
        self.error_label.hide()
        self.success_label.setText(message)
        self.success_label.show()
        
    def clear_messages(self):
        """Bersihkan semua pesan"""
        self.error_label.hide()
        self.success_label.hide()
        
    def validate_name(self, name):
        """Validasi nama lengkap"""
        if not name or len(name.strip()) == 0:
            return "Nama lengkap harus diisi!"
        
        name = name.strip()
        if len(name) < 3:
            return "Nama minimal 3 karakter!"
            
        if len(name.split()) < 2:
            return "Masukkan nama lengkap (minimal 2 kata)!"
            
        # Cek karakter yang diizinkan (huruf, spasi, titik, koma)
        if not re.match(r"^[a-zA-Z\s.,'-]+$", name):
            return "Nama hanya boleh mengandung huruf, spasi, dan tanda baca umum!"
            
        return None
    
    def validate_email(self, email):
        """Validasi email dengan regex yang lebih ketat"""
        if not email or len(email.strip()) == 0:
            return "Email harus diisi!"
            
        email = email.strip().lower()
        
        # Regex pattern untuk email yang valid
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return "Format email tidak valid! Contoh: nama@domain.com"
            
        # Cek domain yang umum
        domain = email.split('@')[1]
        if '.' not in domain:
            return "Domain email tidak valid!"
            
        # Cek panjang email
        if len(email) > 254:
            return "Email terlalu panjang!"
            
        return None
    
    def validate_password(self, password):
        """Validasi password dengan kriteria keamanan"""
        if not password:
            return "Sandi harus diisi!"
            
        if len(password) < 8:
            return "Sandi minimal 8 karakter!"
            
        if len(password) > 128:
            return "Sandi maksimal 128 karakter!"
            
        # Cek ada huruf besar
        if not re.search(r'[A-Z]', password):
            return "Sandi harus mengandung minimal 1 huruf besar!"
            
        # Cek ada huruf kecil
        if not re.search(r'[a-z]', password):
            return "Sandi harus mengandung minimal 1 huruf kecil!"
            
        # Cek ada angka
        if not re.search(r'\d', password):
            return "Sandi harus mengandung minimal 1 angka!"
            
        return None
    
    def validate_confirm_password(self, password, confirm_password):
        """Validasi konfirmasi password"""
        if not confirm_password:
            return "Konfirmasi sandi harus diisi!"
            
        if password != confirm_password:
            return "Konfirmasi sandi tidak cocok dengan sandi!"
            
        return None
    
    def validate_realtime(self):
        """Validasi real-time saat user mengetik"""
        # Reset error message
        self.clear_messages()
        
        # Validasi setiap field dan tampilkan error jika ada
        name = self.name_input.text()
        email = self.email_input.text()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        # Cek field yang sedang difokuskan dan validasi
        if self.name_input.hasFocus() and name:
            error = self.validate_name(name)
            if error:
                self.show_error(error)
                return
                
        if self.email_input.hasFocus() and email:
            error = self.validate_email(email)
            if error:
                self.show_error(error)
                return
                
        if self.password_input.hasFocus() and password:
            error = self.validate_password(password)
            if error:
                self.show_error(error)
                return
                
        if self.confirm_password_input.hasFocus() and confirm_password:
            error = self.validate_confirm_password(password, confirm_password)
            if error:
                self.show_error(error)
                return
    
    def validate_form(self):
        """Validasi lengkap form sebelum submit"""
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        # Validasi nama
        error = self.validate_name(name)
        if error:
            self.show_error(error)
            self.name_input.setFocus()
            return False
            
        # Validasi email
        error = self.validate_email(email)
        if error:
            self.show_error(error)
            self.email_input.setFocus()
            return False
            
        # Validasi password
        error = self.validate_password(password)
        if error:
            self.show_error(error)
            self.password_input.setFocus()
            return False
            
        # Validasi konfirmasi password
        error = self.validate_confirm_password(password, confirm_password)
        if error:
            self.show_error(error)
            self.confirm_password_input.setFocus()
            return False
            
        return True
        
    def attempt_signup(self):
        """Coba melakukan registrasi"""
        self.clear_messages()
        
        if not self.validate_form():
            return
            
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        # Gunakan auth_logic untuk registrasi
        try:
            success, message = register_user(name, email, password, self.role)
            
            if success:
                self.show_success(message)
                
                # Emit signal untuk memberitahu parent
                self.signup_success.emit(name, email, self.role)
                
                # Tutup dialog setelah delay singkat
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(2000, self.accept)
            else:
                self.show_error(message)
                
        except Exception as e:
            self.show_error(f"Error saat mendaftar: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Test dialog
    dialog = SignupPage("customer")
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        print("Signup successful!")
    else:
        print("Signup cancelled!")
    
    sys.exit(app.exec())