"""
Export dialog with pyramidal TIFF support and level selection
"""

import os
from typing import List, Dict, Optional, Tuple
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
                            QRadioButton, QCheckBox, QLabel, QPushButton,
                            QFileDialog, QProgressBar, QMessageBox, QSpinBox,
                            QComboBox, QListWidget, QListWidgetItem, QFrame,
                            QScrollArea, QWidget, QApplication)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from ..core.fragment import Fragment

class ExportDialog(QDialog):
    """Dialog for exporting composite images with format and level selection"""
    
    def __init__(self, fragments: List[Fragment], parent=None):
        super().__init__(parent)
        self.fragments = fragments
        self.selected_levels = []
        self.export_format = 'png'  # Default to PNG
        self.output_path = ""
        self.level_checkboxes = {}  # Initialize this early
        self.common_levels = []
        self.all_available_levels = []
        self.fragment_levels = {}
        
        self.setup_ui()
        self.analyze_pyramid_levels()
        
    def setup_ui(self):
        """Setup the export dialog UI"""
        self.setWindowTitle("Export Composite Image")
        self.setModal(True)
        self.resize(500, 600)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Export Composite Image")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Format selection group
        self.format_group = QGroupBox("Export Format")
        self.setup_format_group()
        layout.addWidget(self.format_group)
        
        # Level selection group (initially hidden)
        self.level_group = QGroupBox("Pyramid Level Selection")
        self.setup_level_group()
        layout.addWidget(self.level_group)
        
        # Export settings group
        self.settings_group = QGroupBox("Export Settings")
        self.setup_settings_group()
        layout.addWidget(self.settings_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.export_button = QPushButton("Export")
        self.export_button.setDefault(True)
        self.export_button.clicked.connect(self.start_export)
        button_layout.addWidget(self.export_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
    def setup_format_group(self):
        """Setup format selection controls"""
        layout = QVBoxLayout(self.format_group)
        
        # PNG option
        self.png_radio = QRadioButton("PNG (Quick Preview)")
        self.png_radio.setChecked(True)
        self.png_radio.toggled.connect(self.on_format_changed)
        layout.addWidget(self.png_radio)
        
        png_desc = QLabel("• Single resolution image\n• Fast export\n• Good for previews and presentations")
        png_desc.setStyleSheet("color: #666; margin-left: 20px; font-size: 11px;")
        layout.addWidget(png_desc)
        
        # Pyramidal TIFF option
        self.tiff_radio = QRadioButton("Pyramidal TIFF (Multi-Resolution)")
        self.tiff_radio.toggled.connect(self.on_format_changed)
        layout.addWidget(self.tiff_radio)
        
        tiff_desc = QLabel("• Multiple resolution levels\n• Compatible with QuPath, ASAP, OpenSlide\n• Larger file size, longer export time")
        tiff_desc.setStyleSheet("color: #666; margin-left: 20px; font-size: 11px;")
        layout.addWidget(tiff_desc)
        
    def setup_level_group(self):
        """Setup pyramid level selection controls"""
        layout = QVBoxLayout(self.level_group)
        
        # Info label
        self.level_info_label = QLabel("Select pyramid levels to export:")
        layout.addWidget(self.level_info_label)
        
        # Scroll area for level checkboxes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(200)
        
        self.level_widget = QWidget()
        self.level_layout = QVBoxLayout(self.level_widget)
        scroll_area.setWidget(self.level_widget)
        layout.addWidget(scroll_area)
        
        # Quick selection buttons
        quick_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_levels)
        quick_layout.addWidget(self.select_all_btn)
        
        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.clicked.connect(self.select_no_levels)
        quick_layout.addWidget(self.select_none_btn)
        
        self.select_common_btn = QPushButton("Select Common")
        self.select_common_btn.clicked.connect(self.select_common_levels)
        quick_layout.addWidget(self.select_common_btn)
        
        layout.addLayout(quick_layout)
        
        # Initially hide the level group
        self.level_group.setVisible(False)
        
    def setup_settings_group(self):
        """Setup export settings controls"""
        layout = QVBoxLayout(self.settings_group)
        
        # Quality setting (for JPEG/PNG)
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Quality:"))
        
        self.quality_spinbox = QSpinBox()
        self.quality_spinbox.setRange(1, 100)
        self.quality_spinbox.setValue(95)
        self.quality_spinbox.setSuffix("%")
        quality_layout.addWidget(self.quality_spinbox)
        quality_layout.addStretch()
        
        layout.addLayout(quality_layout)
        
        # Compression setting (for TIFF)
        compression_layout = QHBoxLayout()
        compression_layout.addWidget(QLabel("Compression:"))
        
        self.compression_combo = QComboBox()
        self.compression_combo.addItems(["None", "LZW", "JPEG", "Deflate"])
        self.compression_combo.setCurrentText("LZW")
        compression_layout.addWidget(self.compression_combo)
        compression_layout.addStretch()
        
        layout.addLayout(compression_layout)
        
    def analyze_pyramid_levels(self):
        """Analyze available pyramid levels across all fragments"""
        if not self.fragments:
            self.populate_level_checkboxes()
            return
            
        # Get pyramid info for each fragment
        fragment_levels = {}
        print("Analyzing pyramid levels for fragments...")
        
        for fragment in self.fragments:
            print(f"Analyzing fragment: {fragment.name}///// { fragment.id}////{ fragment.file_path}???")
            if not fragment.visible or not fragment.file_path:
                continue
                
            try:
                # Get pyramid levels from the original file
                levels = self.get_pyramid_levels(fragment.file_path)
                fragment_levels[fragment.id] = levels
                print(f"Fragment {fragment.name}: levels {levels}")
            except Exception as e:
                print(f"Warning: Could not analyze levels for {fragment.name}: {e}")
                continue
        
        if not fragment_levels:
            print("No fragment levels found")
            self.populate_level_checkboxes()
            return
            
        # Find common levels (levels that exist in ALL fragments)
        all_levels = list(fragment_levels.values())
        if all_levels:
            common_levels = set(all_levels[0])
            for levels in all_levels[1:]:
                common_levels &= set(levels)
            
            self.common_levels = sorted(list(common_levels))
            self.all_available_levels = sorted(list(set().union(*all_levels)))
            self.fragment_levels = fragment_levels
            
            print(f"Common levels: {self.common_levels}")
            print(f"All available levels: {self.all_available_levels}")
        else:
            self.common_levels = []
            self.all_available_levels = []
            self.fragment_levels = {}
            
        self.populate_level_checkboxes()
        
    def get_pyramid_levels(self, file_path: str) -> List[int]:
        """Get available pyramid levels from a TIFF file"""
        try:
            # Use tifffile directly for TIFF files
            import tifffile
            with tifffile.TiffFile(file_path) as tif:
                if hasattr(tif, 'series') and tif.series:
                    series = tif.series[0]
                    if hasattr(series, 'levels') and len(series.levels) > 1:
                        # Pyramidal TIFF
                        return list(range(len(series.levels)))
                    else:
                        # Single level TIFF
                        return [0]  # Single level
                else:
                    return [0]  # Single level
        except Exception as e:
            print(f"tifffile failed for {file_path}: {e}")
            return [0]  # Assume single level
                
    def populate_level_checkboxes(self):
        """Populate the level selection checkboxes"""
        # Clear existing checkboxes
        for i in reversed(range(self.level_layout.count())):
            child = self.level_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        self.level_checkboxes = {}
        
        if not self.all_available_levels:
            no_levels_label = QLabel("No pyramid levels detected in loaded images.")
            no_levels_label.setStyleSheet("color: #888; font-style: italic;")
            self.level_layout.addWidget(no_levels_label)
            return
        
        # Add checkboxes for each level
        for level in self.all_available_levels:
            checkbox = QCheckBox(f"Level {level}")
            
            # Add level info
            level_info = self.get_level_info(level)
            checkbox.setText(f"Level {level} - {level_info}")
            
            # Mark common levels
            if level in self.common_levels:
                checkbox.setStyleSheet("font-weight: bold; color: #4a90e2;")
                checkbox.setToolTip("Available in all loaded fragments")
            else:
                checkbox.setStyleSheet("color: #888;")
                checkbox.setToolTip("Not available in all fragments - may cause issues")
            
            self.level_checkboxes[level] = checkbox
            self.level_layout.addWidget(checkbox)
        
        # Select common levels by default
        self.select_common_levels()
        
    def get_level_info(self, level: int) -> str:
        """Get descriptive info for a pyramid level"""
        if level == 0:
            return "Full Resolution"
        else:
            downsample = 2 ** level
            return f"1/{downsample} Resolution"
            
    def on_format_changed(self):
        """Handle format selection changes"""
        if self.png_radio.isChecked():
            self.export_format = 'png'
            self.level_group.setVisible(False)
        elif self.tiff_radio.isChecked():
            self.export_format = 'pyramidal_tiff'
            self.level_group.setVisible(True)
            
        # Adjust dialog size
        self.adjustSize()
        
    def select_all_levels(self):
        """Select all available levels"""
        for checkbox in self.level_checkboxes.values():
            checkbox.setChecked(True)
            
    def select_no_levels(self):
        """Deselect all levels"""
        for checkbox in self.level_checkboxes.values():
            checkbox.setChecked(False)
            
    def select_common_levels(self):
        """Select only levels common to all fragments"""
        for level, checkbox in self.level_checkboxes.items():
            checkbox.setChecked(level in self.common_levels)
            
    def get_selected_levels(self) -> List[int]:
        """Get list of selected pyramid levels"""
        selected = []
        for level, checkbox in self.level_checkboxes.items():
            if checkbox.isChecked():
                selected.append(level)
        return sorted(selected)
        
    def start_export(self):
        """Start the export process"""
        # Get selected levels for pyramidal TIFF
        if self.export_format == 'pyramidal_tiff':
            self.selected_levels = self.get_selected_levels()
            if not self.selected_levels:
                QMessageBox.warning(self, "No Levels Selected", 
                                  "Please select at least one pyramid level to export.")
                return
        
        # Get output file path
        if self.export_format == 'png':
            file_filter = "PNG files (*.png)"
            default_suffix = ".png"
        else:
            file_filter = "TIFF files (*.tiff *.tif)"
            default_suffix = ".tiff"
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Composite Image", 
            f"composite{default_suffix}", 
            file_filter
        )
        
        if not file_path:
            return
            
        self.output_path = file_path
        
        # Accept dialog and let parent handle the export
        self.accept()
        
    def get_export_settings(self) -> Dict:
        """Get export settings dictionary"""
        return {
            'format': self.export_format,
            'output_path': self.output_path,
            'selected_levels': self.selected_levels,
            'quality': self.quality_spinbox.value(),
            'compression': self.compression_combo.currentText(),
            'common_levels': self.common_levels,
            'fragment_levels': self.fragment_levels
        }