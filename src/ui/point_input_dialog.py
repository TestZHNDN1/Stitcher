"""
Dialog for inputting point labels
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt

class PointInputDialog(QDialog):
    """Dialog for entering point labels"""
    
    def __init__(self, parent=None, existing_labels=None):
        super().__init__(parent)
        self.existing_labels = existing_labels or []
        self.label_text = ""
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Add Labeled Point")
        self.setModal(True)
        self.resize(300, 120)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instruction_label = QLabel("Enter a label for this point:")
        layout.addWidget(instruction_label)
        
        # Label input
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("e.g., P1, anchor_left, corner_top")
        self.label_input.textChanged.connect(self.validate_input)
        layout.addWidget(self.label_input)
        
        # Existing labels info
        if self.existing_labels:
            existing_label = QLabel(f"Existing labels: {', '.join(self.existing_labels)}")
            existing_label.setStyleSheet("color: #666; font-size: 11px;")
            existing_label.setWordWrap(True)
            layout.addWidget(existing_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("Add Point")
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setEnabled(False)
        button_layout.addWidget(self.ok_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        # Focus on input
        self.label_input.setFocus()
        
    def validate_input(self):
        """Validate the input and enable/disable OK button"""
        text = self.label_input.text().strip()
        self.ok_button.setEnabled(len(text) > 0)
        
    def accept(self):
        """Accept the dialog and store the label"""
        self.label_text = self.label_input.text().strip()
        if not self.label_text:
            QMessageBox.warning(self, "Invalid Input", "Please enter a label.")
            return
        super().accept()
        
    def get_label(self) -> str:
        """Get the entered label"""
        return self.label_text