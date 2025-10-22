"""
UI_cs_main.py - Main Customer Dashboard Interface
File utama yang mengintegrasikan semua halaman customer

Komponen:
- Header Bar (hamburger menu + profile)
- Bottom Navigation (Dashboard, Pesan, Profil)
- Sidebar (Dashboard, Simulasi, Keluar)
- Main Content Area (stacked pages)
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QStackedWidget, QSizePolicy,
    QSpacerItem, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QPoint, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QIcon


try:
    from .UI_cs_dashboard import CustomerDashboard
    from .UI_cs_order import OrderDialog
    from .UI_cs_history import CustomerHistory
except ImportError:
    import os
    CURRENT_DIR = os.path.dirname(__file__)
    PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)
    # Fallback absolute imports when running as a script
    from UI.customer.UI_cs_dashboard import CustomerDashboard
    from UI.customer.UI_cs_order import OrderDialog
    from UI.customer.UI_cs_history import CustomerHistory

try:
    try:
        from .UI_cs_order import CustomerOrder
    except ImportError:
        from UI.customer.UI_cs_order import CustomerOrder
except Exception:
    class CustomerOrder(QWidget):
        def __init__(self, current_user: dict | None = None):
            super().__init__()
            self.current_user = current_user or {}
            layout = QVBoxLayout(self)
            label = QLabel("Order/Pesan Page - Under Development")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)

try:
    try:
        from .UI_cs_profile import CustomerProfile
    except ImportError:
        from UI.customer.UI_cs_profile import CustomerProfile
except Exception:
    class CustomerProfile(QWidget):
        def __init__(self, current_user: dict | None = None):
            super().__init__()
            layout = QVBoxLayout(self)
            label = QLabel("Profile Page - Under Development")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)

try:
    try:
        from .UI_cs_simulation import CustomerSimulation
    except ImportError:
        from UI.customer.UI_cs_simulation import CustomerSimulation
except Exception:
    class CustomerSimulation(QWidget):
        def __init__(self):
            super().__init__()
            layout = QVBoxLayout(self)
            label = QLabel("Simulation Page - Under Development")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)


class HeaderBar(QWidget):
    """Header bar dengan hamburger menu dan profile"""
    
    hamburger_clicked = pyqtSignal()
    profile_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()
    
    def __init__(self, username="User", parent=None):
        super().__init__(parent)
        self.username = username
        self.init_ui()
    
    def init_ui(self):
        """Initialize header UI"""
        self.setFixedHeight(60)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("HeaderBar")
      
        self.setStyleSheet(
            "#HeaderBar {"
                "background-color: rgba(210, 245, 250, 0.9);"
            "}"
        )
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)
        
        # Hamburger menu button (3 strips) - lebih jelas
        self.hamburger_btn = QPushButton("≡")
        self.hamburger_btn.setFixedSize(45, 45)
        self.hamburger_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.15);
                color: black;
                font-size: 22px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                outline: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.25);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.35);
            }
            QPushButton:focus {
                outline: none;
                border: none;
            }
        """)
        self.hamburger_btn.clicked.connect(self.hamburger_clicked.emit)

        # Refresh button
        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setFixedSize(45, 45)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.15);
                color: black;
                font-size: 22px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                outline: none;
            }
            QPushButton:hover {
                background-color: #AEDFF7;
                color: #0B3D91;
                border: 1px solid #0B3D91;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.35);
            }
            QPushButton:focus {
                outline: none;
                border: none;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        
        # Spacer
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # Profile section
        profile_widget = QWidget()
        profile_layout = QHBoxLayout(profile_widget)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        profile_layout.setSpacing(5)  # Perkecil jarak
        
        # Profile picture (circle) - diperkecil
        self.profile_pic = QPushButton("●")
        self.profile_pic.setFixedSize(35, 35)
        self.profile_pic.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.9);
                color: #2C3E50;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid white;
                border-radius: 17px;
            }
            QPushButton:hover {
                background-color: white;
                border-color: #E8F4FD;
            }
        """)
        self.profile_pic.clicked.connect(self.profile_clicked.emit)
        
        # Username label
        self.username_label = QLabel(self.username)
        self.username_label.setStyleSheet("""
            QLabel {
                color: black;
                font-size: 14px;
                font-weight: bold;
                padding: 6px 10px;
                border-radius: 12px;
            }
        """)
        
        profile_layout.addWidget(self.profile_pic)
        profile_layout.addWidget(self.username_label)
        
        layout.addWidget(self.hamburger_btn)
        layout.addWidget(self.refresh_btn)
        layout.addItem(spacer)
        layout.addWidget(profile_widget)
    
    def update_username(self, username):
        """Update username display"""
        self.username = username
        self.username_label.setText(username)


class BottomNavigation(QWidget):
    """Bottom navigation bar dengan 3 button"""
    
    page_changed = pyqtSignal(int)  # 0=Dashboard, 1=Pesan, 2=Profil
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 0
        self.buttons = []
        self.init_ui()
    
    def init_ui(self):
        """Initialize bottom navigation UI"""
        self.setFixedHeight(70)
        # Ensure styled background is painted for this widget only
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("BottomNavigation")
        # Apply gradient only to this widget via ID selector so children don't inherit
        self.setStyleSheet(
            "#BottomNavigation {"
            "background-color: rgba(210, 245, 250, 0.9);"
            "}"
        )
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(0)
        
        # Button data: (text, icon, index) - icon vektor hitam
        button_data = [
            ("Dashboard", "🏠", 0),
            ("Pesan", "🛒", 1),
            ("Profil", "👤", 2)
        ]
        
        for text, icon, index in button_data:
            btn = self.create_nav_button(text, icon, index)
            self.buttons.append(btn)
            layout.addWidget(btn)
        
        # Set dashboard as active by default
        self.set_active_button(0)
    
    def create_nav_button(self, text, icon, index):
        """Create navigation button"""
        btn = QPushButton()
        btn.setFixedHeight(60)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Create button layout
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # Icon label
        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 24px; color: #2C3E50;")
        
        # Text label
        text_label = QLabel(text)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setStyleSheet("font-size: 10px; font-weight: bold;")
        
        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        
        btn.setLayout(layout)
        btn.clicked.connect(lambda: self.on_button_clicked(index))
        
        return btn
    
    def on_button_clicked(self, index):
        """Handle button click"""
        self.set_active_button(index)
        self.page_changed.emit(index)
    
    def set_active_button(self, index):
        """Set active button style"""
        self.current_page = index
        
        for i, btn in enumerate(self.buttons):
            if i == index:
                # Active style
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(90, 167, 185, 0.2);;
                        border: none;
                        border-radius: 10px;
                        color: #4A90A4;
                    }
                """)
            else:
                # Inactive style
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        border-radius: 10px;
                        color: #757575;
                    }
                    QPushButton:hover {
                        background-color: #F5F5F5;
                    }
                """)


class Sidebar(QWidget):
    """Sidebar dengan menu navigasi"""
    
    dashboard_clicked = pyqtSignal()
    history_clicked = pyqtSignal()
    simulation_clicked = pyqtSignal()
    logout_clicked = pyqtSignal()
    close_sidebar = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize sidebar UI"""
        self.setFixedWidth(250)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("Sidebar")
        self.setStyleSheet("""
            #Sidebar {
                background-color: rgba(90, 167, 185, 0.5);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Menu buttons - full height tanpa header
        self.menu_layout = QVBoxLayout()
        self.menu_layout.setContentsMargins(15, 30, 15, 15)
        self.menu_layout.setSpacing(15)
        
        # Dashboard button
        self.btn_dashboard = self.create_menu_button("Dashboard")
        self.btn_dashboard.setCheckable(True)
        self.btn_dashboard.clicked.connect(self.dashboard_clicked.emit)
        
        # History button
        self.btn_history = self.create_menu_button("History")
        self.btn_history.setCheckable(True)
        self.btn_history.clicked.connect(self.history_clicked.emit)

        # Simulation button
        self.btn_simulation = self.create_menu_button("Simulasi")
        self.btn_simulation.setCheckable(True)
        self.btn_simulation.clicked.connect(self.simulation_clicked.emit)
        
        self.menu_layout.addWidget(self.btn_dashboard)
        self.menu_layout.addWidget(self.btn_history)
        self.menu_layout.addWidget(self.btn_simulation)
        self.menu_layout.addStretch()
        
        # Logout button (at bottom) - icon vektor hitam
        self.btn_logout = self.create_menu_button("◀ Keluar", is_logout=True)
        self.btn_logout.clicked.connect(self.logout_clicked.emit)
        self.menu_layout.addWidget(self.btn_logout)
        
        layout.addLayout(self.menu_layout)

    def set_active(self, which: str):
        """Set active/checked style for sidebar buttons"""
        mapping = {
            "dashboard": self.btn_dashboard,
            "history": self.btn_history,
            "simulation": self.btn_simulation,
        }
        for key, btn in mapping.items():
            is_active = (key == which)
            btn.setChecked(is_active)
            if is_active:
                btn.setStyleSheet(
                    """
                    QPushButton { background-color: #4682B4; color: white; border: none; border-radius: 12px; text-align: left; padding-left: 20px; font-weight: bold; font-size: 14px; }
                    """
                )
            else:
                btn.setStyleSheet(
                    """
                    QPushButton { background-color: transparent; color: #2C3E50; border: none; border-radius: 12px; text-align: left; padding-left: 20px; font-weight: bold; font-size: 14px; }
                    QPushButton:hover { background-color: #4682B4; color: white; }
                    """
                )
    
    def create_menu_button(self, text, is_logout=False):
        """Create menu button"""
        btn = QPushButton(text)
        btn.setFixedHeight(55)  # Tinggi button ditambah
        btn.setFont(QFont("Segoe UI", 12))
        
        if is_logout:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFEBEE;
                    color: #D32F2F;
                    border: none;
                    border-radius: 12px;
                    text-align: left;
                    padding-left: 20px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #FFCDD2;
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #2C3E50;
                    border: none;
                    border-radius: 12px;
                    text-align: left;
                    padding-left: 20px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #4682B4;
                    color: white;
                }
            """)
        
        return btn


class CustomerMainWindow(QMainWindow):
    """Main customer dashboard window"""
    
    # Signals untuk komunikasi dengan main app
    logout_requested = pyqtSignal()
    simulation_requested = pyqtSignal()
    
    def __init__(self, username="Customer", current_user: dict | None = None, parent=None):
        super().__init__(parent)
        self.username = username
        self.current_user = current_user or {}
        self.sidebar_visible = False
        self.init_ui()
        self.setup_animations()
    
    def init_ui(self):
        """Initialize main UI"""
        self.setWindowTitle("AquaGalon - Customer Dashboard")
        self.setFixedSize(1200, 800)  # Konsisten dengan login
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header bar
        self.header_bar = HeaderBar(self.username)
        self.header_bar.hamburger_clicked.connect(self.toggle_sidebar)
        self.header_bar.profile_clicked.connect(self.show_profile)
        self.header_bar.refresh_clicked.connect(self.refresh_data)
        
        # Content area (sidebar + main content)
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.dashboard_clicked.connect(self.show_dashboard)
        self.sidebar.history_clicked.connect(self.show_history)
        self.sidebar.simulation_clicked.connect(self.show_simulation)
        self.sidebar.logout_clicked.connect(self.logout_requested.emit)
        self.sidebar.hide()  # Hidden by default
        
        # Main content area - background berbeda dari bottom bar
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background-color: white;
            }
        """)
        # Loading overlay di atas seluruh window
        self.loading_overlay = QLabel("Memuat…", parent=self)
        self.loading_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_overlay.setStyleSheet("""
            QLabel {
                background-color: rgba(0,0,0,0.35);
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        self.loading_overlay.hide()
        
        # Initialize pages
        self.dashboard_page = CustomerDashboard(current_user=self.current_user)
        self.history_page = CustomerHistory(current_user=self.current_user)
        self.simulation_page = CustomerSimulation()
        self.order_page = CustomerOrder(current_user=self.current_user)
        self.profile_page = CustomerProfile(current_user=self.current_user)
        
        # Add pages to stack
        self.content_stack.addWidget(self.dashboard_page)   # Index 0
        self.content_stack.addWidget(self.history_page)     # Index 1
        self.content_stack.addWidget(self.simulation_page)  # Index 2
        self.content_stack.addWidget(self.order_page)       # Index 3
        self.content_stack.addWidget(self.profile_page)     # Index 4
        
        # Right container holds main content and bottom nav vertically
        right_container = QWidget()
        right_v = QVBoxLayout(right_container)
        right_v.setContentsMargins(0, 0, 0, 0)
        right_v.setSpacing(0)

        # Bottom navigation
        self.bottom_nav = BottomNavigation()
        self.bottom_nav.page_changed.connect(self.change_page)

        right_v.addWidget(self.content_stack)
        right_v.addWidget(self.bottom_nav)

        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(right_container)
        
        # Add to main layout
        main_layout.addWidget(self.header_bar)
        main_layout.addWidget(content_widget)
        # Pastikan overlay menutupi area window
        self.loading_overlay.raise_()
        
        # Set initial page and sidebar active state
        self.content_stack.setCurrentIndex(0)
        self.sidebar.set_active("dashboard")

    def refresh_data(self):
        """Reload data dari database dengan overlay loading 0.3s."""
        # Tampilkan overlay loading
        self._show_loading()

        def _do_reload():
            try:
                if hasattr(self.dashboard_page, 'set_current_user'):
                    self.dashboard_page.set_current_user(self.current_user)
                elif hasattr(self.dashboard_page, 'reload_orders'):
                    self.dashboard_page.reload_orders()
            except Exception:
                pass
            try:
                if hasattr(self.history_page, 'reload_history'):
                    if hasattr(self.history_page, 'current_user'):
                        self.history_page.current_user = self.current_user
                    self.history_page.reload_history()
            except Exception:
                pass
            # Sembunyikan overlay setelah selesai
            self._hide_loading()

        QTimer.singleShot(300, _do_reload)
    
    def setup_animations(self):
        """Setup sidebar animations"""
        # Animation untuk width sidebar
        self.sidebar_animation = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.sidebar_animation.setDuration(300)
        self.sidebar_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Connect animation finished signal
        self.sidebar_animation.finished.connect(self.on_animation_finished)
        
        # Set initial state
        self.sidebar.setMaximumWidth(0)
        self.sidebar.hide()
        
        # Install event filter untuk click outside
        self.installEventFilter(self)
    
    def toggle_sidebar(self):
        """Toggle sidebar visibility"""
        # Stop any ongoing animation
        if self.sidebar_animation.state() == QPropertyAnimation.State.Running:
            self.sidebar_animation.stop()
        
        if self.sidebar_visible:
            self.hide_sidebar()
        else:
            self.show_sidebar()
    
    def show_sidebar(self):
        """Show sidebar with smooth animation"""
        if not self.sidebar_visible:
            self.sidebar.show()
            self.sidebar.setMaximumWidth(0)  # Start from 0
            self.sidebar_animation.setStartValue(0)
            self.sidebar_animation.setEndValue(250)
            self.sidebar_animation.start()
            self.sidebar_visible = True
    
    def hide_sidebar(self):
        """Hide sidebar with smooth animation"""
        if self.sidebar_visible:
            self.sidebar_animation.setStartValue(250)
            self.sidebar_animation.setEndValue(0)
            self.sidebar_animation.start()
            self.sidebar_visible = False
    
    def on_animation_finished(self):
        """Handle animation finished"""
        if not self.sidebar_visible:
            # Hide sidebar completely when animation to close is finished
            self.sidebar.hide()
    
    def change_page(self, index):
        """Change main content page via bottom nav. Index 1 (Pesan) membuka dialog order."""
        # 0=Dashboard, 1=Pesan, 2=Profil
        if index == 1:
            dlg = OrderDialog(self, current_user=self.current_user)
            # Tampilkan segera tanpa delay
            if dlg.exec():
                # Jika sukses pesan, reload dashboard agar muncul order baru
                try:
                    if hasattr(self, 'dashboard_page') and hasattr(self.dashboard_page, 'reload_orders'):
                        self.dashboard_page.reload_orders()
                except Exception:
                    pass
            # Kembalikan focus ke halaman sebelumnya (tetap di halaman aktif)
            self.bottom_nav.set_active_button(self.content_stack.currentIndex() if self.content_stack else 0)
            return
        # Selain Pesan: ubah halaman
        if index == 2:
            # Profil pada bottom-nav diarahkan ke page profil (index 4)
            self.content_stack.setCurrentIndex(4)
        else:
            self.content_stack.setCurrentIndex(index)

    def set_current_user(self, user: dict | None):
        """Update current user and propagate to pages."""
        self.current_user = user or {}
        try:
            if hasattr(self.dashboard_page, 'set_current_user'):
                self.dashboard_page.set_current_user(self.current_user)
        except Exception:
            pass
        try:
            if hasattr(self.history_page, 'reload_history'):
                # History tidak punya setter; update atribut dan reload
                if hasattr(self.history_page, 'current_user'):
                    self.history_page.current_user = self.current_user
                self.history_page.reload_history()
        except Exception:
            pass
    
    def show_dashboard(self):
        """Show dashboard page (keep sidebar open)"""
        self.content_stack.setCurrentIndex(0)
        self.bottom_nav.set_active_button(0)
        self.bottom_nav.show()
        self.sidebar.set_active("dashboard")

    def show_history(self):
        """Show history page (keep sidebar open)"""
        self.content_stack.setCurrentIndex(1)
        # Sembunyikan bottom nav untuk halaman history
        self.bottom_nav.hide()
        self.sidebar.set_active("history")
        self.update_bottom_nav_for("history")

    def show_simulation(self):
        """Show simulation page (keep sidebar open)"""
        self.content_stack.setCurrentIndex(2)
        # Sembunyikan bottom nav untuk halaman simulasi
        self.bottom_nav.hide()
        self.sidebar.set_active("simulation")
        self.update_bottom_nav_for("simulation")
    
    def show_profile(self):
        """Show profile page"""
        self.content_stack.setCurrentIndex(4)
        self.bottom_nav.set_active_button(2)
        self.bottom_nav.show()

    def update_bottom_nav_for(self, section: str):
        """Temporary: update bottom nav labels per section"""
        try:
            labels_map = {
                "dashboard": ["Dashboard", "Pesan", "Profil"],
                "history": ["History", "Pesan", "Profil"],
                "simulation": ["Simulasi", "Pesan", "Profil"],
            }
            labels = labels_map.get(section, labels_map["dashboard"])
            # Iterate through buttons and update text label if present
            for i, btn in enumerate(self.bottom_nav.buttons):
                # The layout contains icon_label and text_label
                lay = btn.layout()
                if lay and lay.count() >= 2:
                    text_label = lay.itemAt(1).widget()
                    if isinstance(text_label, QLabel):
                        text_label.setText(labels[i] if i < len(labels) else text_label.text())
        except Exception:
            pass
    
    def update_username(self, username):
        """Update displayed username"""
        self.username = username
        self.header_bar.update_username(username)
    
    def get_current_page(self):
        """Get current page index"""
        return self.content_stack.currentIndex()
    
    def resizeEvent(self, event):
        """Pastikan overlay loading selalu menutupi seluruh jendela."""
        super().resizeEvent(event)
        try:
            self.loading_overlay.setGeometry(self.rect())
        except Exception:
            pass

    def _show_loading(self):
        try:
            self.loading_overlay.setGeometry(self.rect())
            self.loading_overlay.show()
            self.loading_overlay.raise_()
        except Exception:
            self.loading_overlay.show()

    def _hide_loading(self):
        self.loading_overlay.hide()

    def eventFilter(self, obj, event):
        """Handle events untuk click outside sidebar"""
        if event.type() == event.Type.MouseButtonPress and self.sidebar_visible:
            # Get click position in global coords (QPoint)
            click_pos = event.globalPosition().toPoint()

            # Build global QRect for sidebar
            sidebar_top_left = self.sidebar.mapToGlobal(QPoint(0, 0))
            sidebar_global_rect = QRect(sidebar_top_left, self.sidebar.size())

            # If click is outside sidebar
            if not sidebar_global_rect.contains(click_pos):
                # Build global QRect for hamburger button
                hb_top_left = self.header_bar.hamburger_btn.mapToGlobal(QPoint(0, 0))
                hb_global_rect = QRect(hb_top_left, self.header_bar.hamburger_btn.size())

                # If click is not on hamburger, hide sidebar
                if not hb_global_rect.contains(click_pos):
                    self.hide_sidebar()
                    return True
        
        return super().eventFilter(obj, event)
    
    def closeEvent(self, event):
        """Handle window close event: close normally (no auto-logout)"""
        event.accept()


# Factory function untuk kemudahan penggunaan
def create_customer_dashboard(current_user: dict | str | None = None) -> CustomerMainWindow:
    """
    Factory function untuk membuat customer dashboard.
    Dapat menerima:
    - dict: {"name": ..., "email": ...}
    - string: username saja (akan dipetakan ke {"name": username})
    - None: fallback ke default.
    """
    if isinstance(current_user, dict):
        username = current_user.get("name", "Customer") or "Customer"
        return CustomerMainWindow(username=username, current_user=current_user)
    elif isinstance(current_user, str) and current_user:
        return CustomerMainWindow(username=current_user, current_user={"name": current_user})
    else:
        return CustomerMainWindow("Customer", current_user={})


# Test function
def test_customer_dashboard():
    """Test function untuk development"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create dashboard as Guest person (bypass login)
    dashboard = create_customer_dashboard({
        "name": "Guest person",
        "email": "guest@gmail.com",
        "role": "customer"
    })
    
    # Connect signals for testing
    def on_logout():
        print("Logout requested")
        app.quit()
    
    def on_simulation():
        print("Simulation requested")
    
    dashboard.logout_requested.connect(on_logout)
    dashboard.simulation_requested.connect(on_simulation)
    
    dashboard.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    test_customer_dashboard()
