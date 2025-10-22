import json
import os
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class AuthenticationError(Exception):
    """Custom exception untuk error autentikasi"""
    pass


class ValidationError(Exception):
    """Custom exception untuk error validasi"""
    pass


class AuthManager:
    """Manager untuk mengelola autentikasi user"""
    
    def __init__(self, db_path: str = "Database/user_acc.json"):
        self.db_path = db_path
        self.ensure_database_exists()
    
    def ensure_database_exists(self):
        """Pastikan file database ada, jika tidak buat yang baru"""
        if not os.path.exists(self.db_path):
            # Buat direktori jika belum ada
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Buat struktur database awal
            initial_data = {
                "users": [],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "total_users": 0
                }
            }
            
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=4, ensure_ascii=False)
    
    def load_database(self) -> Dict:
        """Load data dari file JSON"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise AuthenticationError(f"Error loading database: {e}")
    
    def save_database(self, data: Dict):
        """Simpan data ke file JSON"""
        try:
            # Update metadata
            data["metadata"]["last_updated"] = datetime.now().isoformat()
            data["metadata"]["total_users"] = len(data["users"])
            
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise AuthenticationError(f"Error saving database: {e}")
    
    def hash_password(self, password: str) -> str:
        """Hash password menggunakan SHA-256 dengan salt"""
        # Gunakan salt sederhana untuk demo
        salt = "aquagalon_salt_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def validate_email(self, email: str) -> bool:
        """Validasi format email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email.lower()) is not None
    
    def validate_password(self, password: str) -> Tuple[bool, str]:
        """Validasi password dengan kriteria keamanan"""
        if len(password) < 8:
            return False, "Password minimal 8 karakter"
        
        if len(password) > 128:
            return False, "Password maksimal 128 karakter"
        
        if not re.search(r'[A-Z]', password):
            return False, "Password harus mengandung minimal 1 huruf besar"
        
        if not re.search(r'[a-z]', password):
            return False, "Password harus mengandung minimal 1 huruf kecil"
        
        if not re.search(r'\d', password):
            return False, "Password harus mengandung minimal 1 angka"
        
        return True, "Password valid"
    
    def validate_name(self, name: str) -> Tuple[bool, str]:
        """Validasi nama lengkap"""
        name = name.strip()
        
        if len(name) < 3:
            return False, "Nama minimal 3 karakter"
        
        if len(name.split()) < 2:
            return False, "Masukkan nama lengkap (minimal 2 kata)"
        
        if not re.match(r"^[a-zA-Z\s.,'-]+$", name):
            return False, "Nama hanya boleh mengandung huruf, spasi, dan tanda baca umum"
        
        return True, "Nama valid"
    
    def email_exists(self, email: str) -> bool:
        """Cek apakah email sudah terdaftar"""
        data = self.load_database()
        email_lower = email.lower()
        
        for user in data["users"]:
            if user["email"].lower() == email_lower:
                return True
        
        return False
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Ambil data user berdasarkan email"""
        data = self.load_database()
        email_lower = email.lower()
        
        for user in data["users"]:
            if user["email"].lower() == email_lower:
                return user
        
        return None
    
    def register_user(self, name: str, email: str, password: str, role: str = "customer") -> Tuple[bool, str]:
        """Daftarkan user baru"""
        try:
            # Validasi input
            name = name.strip()
            email = email.strip().lower()
            
            # Validasi nama
            is_valid, message = self.validate_name(name)
            if not is_valid:
                return False, message
            
            # Validasi email format
            if not self.validate_email(email):
                return False, "Format email tidak valid"
            
            # Cek apakah email sudah terdaftar
            if self.email_exists(email):
                return False, "Email sudah terdaftar. Silakan gunakan email lain atau login."
            
            # Validasi password
            is_valid, message = self.validate_password(password)
            if not is_valid:
                return False, message
            
            # Validasi role
            if role not in ["customer", "seller"]:
                return False, "Role harus customer atau seller"
            
            # Load database
            data = self.load_database()
            
            # Buat user baru
            new_user = {
                "id": len(data["users"]) + 1,
                "name": name,
                "email": email,
                "password": self.hash_password(password),
                "role": role,
                "created_at": datetime.now().isoformat(),
                "last_login": None,
                "is_active": True
            }
            
            # Tambahkan ke database
            data["users"].append(new_user)
            
            # Simpan database
            self.save_database(data)
            
            return True, f"Akun berhasil dibuat untuk {name} ({email})"
            
        except Exception as e:
            return False, f"Error saat mendaftar: {str(e)}"
    
    def authenticate_user(self, email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """Autentikasi user login"""
        try:
            # Validasi input
            email = email.strip().lower()
            
            # Validasi email format
            if not self.validate_email(email):
                return False, "Format email tidak valid", None
            
            # Cari user
            user = self.get_user_by_email(email)
            if not user:
                return False, "Email tidak terdaftar. Silakan daftar terlebih dahulu.", None
            
            # Cek apakah akun aktif
            if not user.get("is_active", True):
                return False, "Akun Anda telah dinonaktifkan. Hubungi administrator.", None
            
            # Verifikasi password
            hashed_password = self.hash_password(password)
            if user["password"] != hashed_password:
                return False, "Password salah. Periksa kembali password Anda.", None
            
            # Update last login
            self.update_last_login(email)
            
            # Return user data tanpa password
            user_data = {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "created_at": user["created_at"],
                "last_login": datetime.now().isoformat()
            }
            
            return True, f"Login berhasil. Selamat datang, {user['name']}!", user_data
            
        except Exception as e:
            return False, f"Error saat login: {str(e)}", None
    
    def update_last_login(self, email: str):
        """Update waktu login terakhir"""
        try:
            data = self.load_database()
            email_lower = email.lower()
            
            for user in data["users"]:
                if user["email"].lower() == email_lower:
                    user["last_login"] = datetime.now().isoformat()
                    break
            
            self.save_database(data)
        except Exception:
            # Jangan gagalkan login jika update last_login gagal
            pass
    
    def change_password(self, email: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Ubah password user"""
        try:
            # Autentikasi dengan password lama
            is_auth, message, user_data = self.authenticate_user(email, old_password)
            if not is_auth:
                return False, "Password lama tidak benar"
            
            # Validasi password baru
            is_valid, message = self.validate_password(new_password)
            if not is_valid:
                return False, message
            
            # Update password
            data = self.load_database()
            email_lower = email.lower()
            
            for user in data["users"]:
                if user["email"].lower() == email_lower:
                    user["password"] = self.hash_password(new_password)
                    break
            
            self.save_database(data)
            return True, "Password berhasil diubah"
            
        except Exception as e:
            return False, f"Error saat mengubah password: {str(e)}"
    
    def deactivate_user(self, email: str) -> Tuple[bool, str]:
        """Nonaktifkan user"""
        try:
            data = self.load_database()
            email_lower = email.lower()
            
            for user in data["users"]:
                if user["email"].lower() == email_lower:
                    user["is_active"] = False
                    self.save_database(data)
                    return True, f"User {email} berhasil dinonaktifkan"
            
            return False, "User tidak ditemukan"
            
        except Exception as e:
            return False, f"Error saat menonaktifkan user: {str(e)}"
    
    def get_all_users(self) -> List[Dict]:
        """Ambil semua data user (tanpa password)"""
        try:
            data = self.load_database()
            users = []
            
            for user in data["users"]:
                user_data = {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "role": user["role"],
                    "created_at": user["created_at"],
                    "last_login": user.get("last_login"),
                    "is_active": user.get("is_active", True)
                }
                users.append(user_data)
            
            return users
            
        except Exception as e:
            raise AuthenticationError(f"Error saat mengambil data user: {str(e)}")
    
    def get_database_stats(self) -> Dict:
        """Ambil statistik database"""
        try:
            data = self.load_database()
            
            total_users = len(data["users"])
            active_users = sum(1 for user in data["users"] if user.get("is_active", True))
            customers = sum(1 for user in data["users"] if user["role"] == "customer")
            sellers = sum(1 for user in data["users"] if user["role"] == "seller")
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users,
                "customers": customers,
                "sellers": sellers,
                "created_at": data["metadata"]["created_at"],
                "last_updated": data["metadata"]["last_updated"]
            }
            
        except Exception as e:
            raise AuthenticationError(f"Error saat mengambil statistik: {str(e)}")


# Fungsi helper untuk kemudahan penggunaan
def create_auth_manager(db_path: str = "Database/user_acc.json") -> AuthManager:
    """Factory function untuk membuat AuthManager"""
    return AuthManager(db_path)


# Instance global untuk penggunaan mudah
auth_manager = create_auth_manager()


# Fungsi wrapper untuk kemudahan
def register_user(name: str, email: str, password: str, role: str = "customer") -> Tuple[bool, str]:
    """Wrapper function untuk registrasi user"""
    return auth_manager.register_user(name, email, password, role)


def login_user(email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
    """Wrapper function untuk login user"""
    return auth_manager.authenticate_user(email, password)


def email_exists(email: str) -> bool:
    """Wrapper function untuk cek email"""
    return auth_manager.email_exists(email)


def get_user_by_email(email: str) -> Optional[Dict]:
    """Wrapper function untuk ambil user"""
    return auth_manager.get_user_by_email(email)


if __name__ == "__main__":
    # Test basic functionality
    print("Testing AuthManager...")
    
    # Test registrasi
    success, message = register_user("John Doe", "john@example.com", "Password123", "customer")
    print(f"Register: {success} - {message}")
    
    # Test login
    success, message, user_data = login_user("john@example.com", "Password123")
    print(f"Login: {success} - {message}")
    if user_data:
        print(f"User data: {user_data}")
    
    # Test email exists
    exists = email_exists("john@example.com")
    print(f"Email exists: {exists}")
    
    print("Testing completed!")
