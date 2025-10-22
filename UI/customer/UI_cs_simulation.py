"""
UI_cs_simulation.py
Halaman Simulasi (PyQt6) – hanya menampilkan informasi bahwa simulasi dilakukan oleh penjual.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class CustomerSimulation(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel("Simulasi hanya dilakukan oleh Penjual")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f5b6b;")

        layout.addWidget(label)
