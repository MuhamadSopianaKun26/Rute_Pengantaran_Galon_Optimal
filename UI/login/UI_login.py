"""
UI_login.py - Main Login Interface Integration
File utama yang mengintegrasikan semua komponen login

Menggabungkan:
- LoginPage (UI_login_page.py)
- SignupPage (UI_signup_page.py) 
- LoginController (login_controller.py)
- Auth Logic (logic/file/auth_logic.py)
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

# Import semua komponen login
try:
    # Relative import untuk penggunaan sebagai module
    from .UI_login_page import LoginPage
    from .login_controller import LoginController
    from logic.file.auth_logic import AuthManager, register_user, login_user
except ImportError:
    # Absolute import untuk standalone testing
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    from UI.login.UI_login_page import LoginPage
    from UI.login.login_controller import LoginController
    
    try:
        from logic.file.auth_logic import AuthManager, register_user, login_user
    except ImportError:
        print("Warning: Auth logic not found. Using fallback mode.")
        # Fallback functions
        def register_user(name, email, password, role):
            return True, "Registrasi berhasil (mode demo)"
        
        def login_user(email, password):
            return True, "Login berhasil (mode demo)", {"name": "Demo User", "email": email, "role": "customer"}


class LoginSystem(QObject):
    """
    Main Login System Class
    Mengintegrasikan semua komponen login dalam satu interface
    """
    
    # Signals untuk komunikasi dengan main app
    login_successful = pyqtSignal(str, dict)  # role, user_data
    login_cancelled = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.login_controller = None
        self.auth_manager = None
        self.init_system()
    
    def init_system(self):
        """Initialize login system"""
        try:
            # Initialize auth manager
            self.auth_manager = AuthManager()
            print("Auth system initialized successfully")
        except Exception as e:
            print(f"Warning: Auth system initialization failed: {e}")
            self.auth_manager = None
    
    def show_login(self):
        """
        Tampilkan interface login
        Method utama yang dipanggil dari main app
        """
        try:
            # Buat login controller
            self.login_controller = LoginController()
            
            # Connect signals
            self.login_controller.login_successful.connect(self.on_login_success)
            self.login_controller.login_cancelled.connect(self.on_login_cancelled)
            
            # Tampilkan login
            self.login_controller.show_login()
            
        except Exception as e:
            print(f"Error showing login: {e}")
            # Fallback: tampilkan login page langsung
            self.show_login_fallback()
    
    def show_login_fallback(self):
        """Fallback method jika login controller gagal"""
        try:
            self.login_page = LoginPage()
            self.login_page.login_success.connect(self.on_login_success)
            self.login_page.window_closed.connect(self.on_login_cancelled)
            self.login_page.show()
        except Exception as e:
            print(f"Critical error: Cannot show login interface: {e}")
            self.login_cancelled.emit()
    
    def on_login_success(self, role: str, user_data: dict):
        """Handle login berhasil"""
        print(f"Login successful: {user_data.get('name')} as {role}")
        
        # Cleanup
        self.cleanup()
        
        # Emit signal ke main app
        self.login_successful.emit(role, user_data)
    
    def on_login_cancelled(self):
        """Handle login dibatalkan"""
        print("Login cancelled")
        
        # Cleanup
        self.cleanup()
        
        # Emit signal ke main app
        self.login_cancelled.emit()
    
    def cleanup(self):
        """Bersihkan resources"""
        if self.login_controller:
            self.login_controller.cleanup()
            self.login_controller = None
        
        if hasattr(self, 'login_page'):
            self.login_page.close()
            delattr(self, 'login_page')
    
    def get_auth_manager(self):
        """Ambil auth manager instance"""
        return self.auth_manager
    
    def get_database_stats(self):
        """Ambil statistik database"""
        if self.auth_manager:
            try:
                return self.auth_manager.get_database_stats()
            except Exception as e:
                print(f"Error getting database stats: {e}")
                return None
        return None


# Factory function untuk kemudahan penggunaan
def create_login_system() -> LoginSystem:
    """
    Factory function untuk membuat LoginSystem
    Ini adalah function utama yang dipanggil dari main app
    """
    return LoginSystem()


# Convenience functions untuk backward compatibility
def show_login_interface():
    """
    Convenience function untuk menampilkan login
    Returns: LoginSystem instance
    """
    login_system = create_login_system()
    login_system.show_login()
    return login_system


def get_auth_system():
    """
    Convenience function untuk mendapatkan auth system
    Returns: AuthManager instance atau None
    """
    try:
        return AuthManager()
    except Exception as e:
        print(f"Error creating auth system: {e}")
        return None


# Test function
def test_login_system():
    """Test function untuk development"""
    print("Testing Login System...")
    
    app = QApplication(sys.argv)
    
    # Test auth system
    auth_manager = get_auth_system()
    if auth_manager:
        stats = auth_manager.get_database_stats()
        print(f"Database stats: {stats}")
    
    # Test login interface
    login_system = create_login_system()
    
    def on_success(role, username):
        print(f"Test: Login successful - {username} ({role})")
        app.quit()
    
    def on_cancelled():
        print("Test: Login cancelled")
        app.quit()
    
    login_system.login_successful.connect(on_success)
    login_system.login_cancelled.connect(on_cancelled)
    
    login_system.show_login()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    test_login_system()
