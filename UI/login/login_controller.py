"""
Login Controller untuk mengelola alur autentikasi
Menghubungkan LoginPage dan SignupPage
"""

from PyQt6.QtCore import QObject, pyqtSignal
from .UI_login_page import LoginPage
from .UI_signup_page import SignupPage


class LoginController(QObject):
    """Controller untuk mengelola proses login dan signup"""
    
    # Signals
    login_successful = pyqtSignal(str, dict)  # role, user_data
    login_cancelled = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.login_page = None
        self.signup_dialog = None
        
    def show_login(self):
        """Tampilkan halaman login"""
        self.login_page = LoginPage()
        
        # Connect signals
        self.login_page.login_success.connect(self.on_login_success)
        self.login_page.open_signup.connect(self.show_signup)
        self.login_page.window_closed.connect(self.on_login_cancelled)
        
        # Show login page
        self.login_page.show()
        
    def show_signup(self):
        """Tampilkan dialog signup"""
        if not self.login_page:
            return
            
        # Ambil role yang dipilih dari login page
        selected_role = getattr(self.login_page, 'selected_role', 'customer')
        
        # Buat dan tampilkan signup dialog
        self.signup_dialog = SignupPage(selected_role, self.login_page)
        
        # Connect signals
        self.signup_dialog.signup_success.connect(self.on_signup_success)
        
        # Show dialog
        self.signup_dialog.exec()
        
    def on_login_success(self, role: str, user_data: dict):
        """Handle login berhasil"""
        self.login_successful.emit(role, user_data)
        
        # Tutup login page secara programmatic (tanpa konfirmasi)
        if self.login_page:
            self.login_page.close_programmatically()
            
    def on_signup_success(self, name, email, role):
        """Handle signup berhasil"""
        print(f"Signup successful: {name} ({email}) as {role}")
        
        # Bisa menambahkan logic untuk auto-login setelah signup
        # atau kembali ke halaman login
        
    def on_login_cancelled(self):
        """Handle ketika login page ditutup secara manual"""
        self.login_cancelled.emit()
        
    def cleanup(self):
        """Bersihkan resources"""
        if self.login_page:
            self.login_page.close()
            self.login_page = None
            
        if self.signup_dialog:
            self.signup_dialog.close()
            self.signup_dialog = None
