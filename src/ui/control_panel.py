"""
Control panel for fragment manipulation
"""

from typing import Optional, List
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                            QPushButton, QLabel, QSpinBox, QDoubleSpinBox,
                            QSlider, QCheckBox, QGridLayout, QTabWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from ..core.fragment import Fragment

class ControlPanel(QWidget):
    """Control panel for fragment transformation and properties"""
    
    transform_requested = pyqtSignal(str, str, object)  # fragment_id, transform_type, value
    reset_transform_requested = pyqtSignal(str)  # fragment_id
    
    def __init__(self):
        super().__init__()
        self.current_fragment: Optional[Fragment] = None
        
        # Group selection state
        self.selected_fragment_ids: List[str] = []
        self.is_group_selected = False
        
        self.setup_ui()
        self.update_controls()
        
    def setup_ui(self):
        """Setup the control panel UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Single fragment tab
        self.fragment_tab = QWidget()
        self.setup_fragment_tab()
        self.tab_widget.addTab(self.fragment_tab, "Fragment")
        
        # Group selection tab
        self.group_tab = QWidget()
        self.setup_group_tab()
        self.tab_widget.addTab(self.group_tab, "Group")
        
        # Add stretch to push everything to top
        layout.addStretch()
        
    def setup_fragment_tab(self):
        """Setup the single fragment controls tab"""
        layout = QVBoxLayout(self.fragment_tab)
        layout.setSpacing(10)
        
        # Fragment info group
        self.info_group = QGroupBox("Fragment Information")
        self.setup_info_group()
        layout.addWidget(self.info_group)
        
        # Transform group
        self.transform_group = QGroupBox("Transformations")
        self.setup_transform_group()
        layout.addWidget(self.transform_group)
        
        # Position group
        self.position_group = QGroupBox("Position")
        self.setup_position_group()
        layout.addWidget(self.position_group)
        
        # Display group
        self.display_group = QGroupBox("Display")
        self.setup_display_group()
        layout.addWidget(self.display_group)
        
    def setup_group_tab(self):
        """Setup the group selection controls tab"""
        layout = QVBoxLayout(self.group_tab)
        layout.setSpacing(10)
        
        # Group info
        self.group_info_group = QGroupBox("Group Information")
        group_info_layout = QVBoxLayout(self.group_info_group)
        
        self.group_name_label = QLabel("No group selected")
        self.group_name_label.setStyleSheet("font-weight: bold; color: #4a90e2;")
        group_info_layout.addWidget(self.group_name_label)
        
        layout.addWidget(self.group_info_group)
        
        # Group rotation controls
        self.group_rotation_group = QGroupBox("Group Rotation")
        rotation_layout = QVBoxLayout(self.group_rotation_group)
        
        # Large rotation buttons
        rotation_buttons_layout = QHBoxLayout()
        
        self.group_rotate_ccw_btn = QPushButton("↺ 90° CCW")
        self.group_rotate_ccw_btn.setMinimumHeight(50)
        self.group_rotate_ccw_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                background-color: #4a90e2;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5a9bd4;
            }
            QPushButton:pressed {
                background-color: #3a80d2;
            }
        """)
        self.group_rotate_ccw_btn.clicked.connect(lambda: self.request_group_rotation('ccw'))
        rotation_buttons_layout.addWidget(self.group_rotate_ccw_btn)
        
        self.group_rotate_cw_btn = QPushButton("↻ 90° CW")
        self.group_rotate_cw_btn.setMinimumHeight(50)
        self.group_rotate_cw_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                background-color: #4a90e2;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5a9bd4;
            }
            QPushButton:pressed {
                background-color: #3a80d2;
            }
        """)
        self.group_rotate_cw_btn.clicked.connect(lambda: self.request_group_rotation('cw'))
        rotation_buttons_layout.addWidget(self.group_rotate_cw_btn)
        
        rotation_layout.addLayout(rotation_buttons_layout)
        layout.addWidget(self.group_rotation_group)
        
        # Group movement controls
        self.group_movement_group = QGroupBox("Group Movement")
        movement_layout = QVBoxLayout(self.group_movement_group)
        
        # Movement buttons grid
        movement_grid = QGridLayout()
        
        # Up
        self.group_up_btn = QPushButton("↑")
        self.group_up_btn.setMinimumSize(40, 40)
        self.group_up_btn.clicked.connect(lambda: self.request_group_translation(0, -10))
        movement_grid.addWidget(self.group_up_btn, 0, 1)
        
        # Left, Center, Right
        self.group_left_btn = QPushButton("←")
        self.group_left_btn.setMinimumSize(40, 40)
        self.group_left_btn.clicked.connect(lambda: self.request_group_translation(-10, 0))
        movement_grid.addWidget(self.group_left_btn, 1, 0)
        
        self.group_center_btn = QPushButton("⌂")
        self.group_center_btn.setMinimumSize(40, 40)
        self.group_center_btn.setToolTip("Center group")
        self.group_center_btn.clicked.connect(lambda: self.request_group_translation(0, 0))
        movement_grid.addWidget(self.group_center_btn, 1, 1)
        
        self.group_right_btn = QPushButton("→")
        self.group_right_btn.setMinimumSize(40, 40)
        self.group_right_btn.clicked.connect(lambda: self.request_group_translation(10, 0))
        movement_grid.addWidget(self.group_right_btn, 1, 2)
        
        # Down
        self.group_down_btn = QPushButton("↓")
        self.group_down_btn.setMinimumSize(40, 40)
        self.group_down_btn.clicked.connect(lambda: self.request_group_translation(0, 10))
        movement_grid.addWidget(self.group_down_btn, 2, 1)
        
        movement_layout.addLayout(movement_grid)
        layout.addWidget(self.group_movement_group)
        
        # Group reset button
        self.group_reset_btn = QPushButton("Reset All Group Transforms")
        self.group_reset_btn.setMinimumHeight(40)
        self.group_reset_btn.setStyleSheet("QPushButton { background-color: #d32f2f; color: white; font-weight: bold; }")
        self.group_reset_btn.clicked.connect(self.request_group_reset)
        layout.addWidget(self.group_reset_btn)
        
    def request_group_rotation(self, direction: str):
        """Request group rotation"""
        print(f"request_group_rotation called: {direction}, group_selected: {self.is_group_selected}, ids: {self.selected_fragment_ids}")
        if self.is_group_selected and self.selected_fragment_ids:
            if direction == 'cw':
                print("Emitting group rotate_cw signal")
                self.transform_requested.emit('group', 'rotate_cw', self.selected_fragment_ids)
            elif direction == 'ccw':
                print("Emitting group rotate_ccw signal")
                self.transform_requested.emit('group', 'rotate_ccw', self.selected_fragment_ids)
    
    def request_group_translation(self, dx: float, dy: float):
        """Request group translation"""
        print(f"request_group_translation called: dx={dx}, dy={dy}, group_selected: {self.is_group_selected}, ids: {self.selected_fragment_ids}")
        if self.is_group_selected and self.selected_fragment_ids:
            print("Emitting group translate signal")
            self.transform_requested.emit('group', 'translate', (self.selected_fragment_ids, (dx, dy)))
    
    def setup_info_group(self):
        """Setup fragment information display"""
        layout = QVBoxLayout(self.info_group)
        
        self.name_label = QLabel("No fragment selected")
        self.name_label.setStyleSheet("font-weight: bold; color: #4a90e2;")
        layout.addWidget(self.name_label)
        
        self.size_label = QLabel("Size: -")
        layout.addWidget(self.size_label)
        
        self.file_label = QLabel("File: -")
        self.file_label.setWordWrap(True)
        layout.addWidget(self.file_label)
        
    def setup_transform_group(self):
        """Setup transformation controls"""
        layout = QGridLayout(self.transform_group)
        
        # Rotation controls
        layout.addWidget(QLabel("Rotation:"), 0, 0)
        
        rotation_layout = QHBoxLayout()
        self.rotate_ccw_btn = QPushButton("↺ 90°")
        self.rotate_ccw_btn.setToolTip("Rotate counter-clockwise")
        self.rotate_ccw_btn.clicked.connect(lambda: self.request_transform('rotate_ccw'))
        rotation_layout.addWidget(self.rotate_ccw_btn)
        
        self.rotate_cw_btn = QPushButton("↻ 90°")
        self.rotate_cw_btn.setToolTip("Rotate clockwise")
        self.rotate_cw_btn.clicked.connect(lambda: self.request_transform('rotate_cw'))
        rotation_layout.addWidget(self.rotate_cw_btn)
        
        layout.addLayout(rotation_layout, 0, 1)
        
        # Free rotation control
        layout.addWidget(QLabel("Angle:"), 1, 0)
        
        angle_layout = QHBoxLayout()
        self.angle_spinbox = QDoubleSpinBox()
        self.angle_spinbox.setRange(-360.0, 360.0)
        self.angle_spinbox.setDecimals(1)
        self.angle_spinbox.setSuffix("°")
        self.angle_spinbox.valueChanged.connect(self.on_angle_changed)
        angle_layout.addWidget(self.angle_spinbox)
        
        # Quick angle buttons (45° - will be disabled for groups)
        angle_45_btn = QPushButton("45°")
        angle_45_btn.setToolTip("Rotate 45 degrees")
        angle_45_btn.clicked.connect(lambda: self.request_transform('rotate_angle', 45))
        self.angle_45_btn = angle_45_btn  # Store reference for enabling/disabling
        angle_layout.addWidget(angle_45_btn)
        
        angle_neg45_btn = QPushButton("-45°")
        angle_neg45_btn.setToolTip("Rotate -45 degrees")
        angle_neg45_btn.clicked.connect(lambda: self.request_transform('rotate_angle', -45))
        self.angle_neg45_btn = angle_neg45_btn  # Store reference for enabling/disabling
        angle_layout.addWidget(angle_neg45_btn)
        
        layout.addLayout(angle_layout, 1, 1)
        
        # Flip controls
        layout.addWidget(QLabel("Flip:"), 2, 0)
        
        flip_layout = QHBoxLayout()
        self.flip_h_btn = QPushButton("↔ Horizontal")
        self.flip_h_btn.setToolTip("Flip horizontally")
        self.flip_h_btn.clicked.connect(lambda: self.request_transform('flip_horizontal'))
        flip_layout.addWidget(self.flip_h_btn)
        
        self.flip_v_btn = QPushButton("↕ Vertical")
        self.flip_v_btn.setToolTip("Flip vertically")
        self.flip_v_btn.clicked.connect(lambda: self.request_transform('flip_vertical'))
        flip_layout.addWidget(self.flip_v_btn)
        
        layout.addLayout(flip_layout, 2, 1)
        
        # Reset button
        self.reset_btn = QPushButton("Reset All Transforms")
        self.reset_btn.setStyleSheet("QPushButton { background-color: #d32f2f; }")
        self.reset_btn.clicked.connect(self.request_reset)
        layout.addWidget(self.reset_btn, 3, 0, 1, 2)
        
    def setup_position_group(self):
        """Setup position controls"""
        layout = QGridLayout(self.position_group)
        
        # X position
        layout.addWidget(QLabel("X:"), 0, 0)
        self.x_spinbox = QDoubleSpinBox()
        self.x_spinbox.setRange(-999999, 999999)
        self.x_spinbox.setDecimals(1)
        self.x_spinbox.valueChanged.connect(self.on_position_changed)
        layout.addWidget(self.x_spinbox, 0, 1)
        
        # Y position
        layout.addWidget(QLabel("Y:"), 1, 0)
        self.y_spinbox = QDoubleSpinBox()
        self.y_spinbox.setRange(-999999, 999999)
        self.y_spinbox.setDecimals(1)
        self.y_spinbox.valueChanged.connect(self.on_position_changed)
        layout.addWidget(self.y_spinbox, 1, 1)
        
        # Translation buttons
        translation_layout = QGridLayout()
        
        # Up
        self.up_btn = QPushButton("↑")
        self.up_btn.clicked.connect(lambda: self.request_transform('translate', (0, -10)))
        translation_layout.addWidget(self.up_btn, 0, 1)
        
        # Left, Center, Right
        self.left_btn = QPushButton("←")
        self.left_btn.clicked.connect(lambda: self.request_transform('translate', (-10, 0)))
        translation_layout.addWidget(self.left_btn, 1, 0)
        
        self.center_btn = QPushButton("⌂")
        self.center_btn.setToolTip("Center fragment")
        self.center_btn.clicked.connect(lambda: self.request_transform('translate', (0, 0)))
        translation_layout.addWidget(self.center_btn, 1, 1)
        
        self.right_btn = QPushButton("→")
        self.right_btn.clicked.connect(lambda: self.request_transform('translate', (10, 0)))
        translation_layout.addWidget(self.right_btn, 1, 2)
        
        # Down
        self.down_btn = QPushButton("↓")
        self.down_btn.clicked.connect(lambda: self.request_transform('translate', (0, 10)))
        translation_layout.addWidget(self.down_btn, 2, 1)
        
        layout.addLayout(translation_layout, 2, 0, 1, 2)
        
    def setup_display_group(self):
        """Setup display controls"""
        layout = QVBoxLayout(self.display_group)
        
        # Visibility checkbox
        self.visible_checkbox = QCheckBox("Visible")
        self.visible_checkbox.stateChanged.connect(self.on_visibility_changed)
        layout.addWidget(self.visible_checkbox)
        
        # Opacity slider
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity:"))
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_label = QLabel("100%")
        self.opacity_label.setMinimumWidth(40)
        opacity_layout.addWidget(self.opacity_label)
        
        layout.addLayout(opacity_layout)
        
    def set_selected_fragment(self, fragment: Optional[Fragment]):
        """Set the currently selected fragment"""
        self.current_fragment = fragment
        self.selected_fragment_ids = []
        self.is_group_selected = False
        
        # Switch to fragment tab
        self.tab_widget.setCurrentWidget(self.fragment_tab)
        self.group_tab.setEnabled(False)
        self.fragment_tab.setEnabled(True)
        
        self.update_controls()
    
    def set_selected_fragments(self, fragment_ids: List[str], fragments: List[Fragment]):
        """Set multiple selected fragments (group selection)"""
        self.selected_fragment_ids = fragment_ids
        self.is_group_selected = len(fragment_ids) > 1
        self.current_fragment = fragments[0] if fragments else None  # Use first fragment for display
        
        if self.is_group_selected:
            # Switch to group tab
            self.tab_widget.setCurrentWidget(self.group_tab)
            self.group_tab.setEnabled(True)
            self.fragment_tab.setEnabled(False)
            
            # Update group info
            self.group_name_label.setText(f"Group Selection ({len(fragment_ids)} fragments)")
        
        self.update_controls()
        
    def update_controls(self):
        """Update control states based on current fragment"""
        has_fragment = self.current_fragment is not None or self.is_group_selected
        
        if self.is_group_selected:
            # Enable all group controls
            self.group_rotation_group.setEnabled(True)
            self.group_movement_group.setEnabled(True)
            self.group_reset_btn.setEnabled(True)
            
            # Enable individual group buttons
            self.group_rotate_ccw_btn.setEnabled(True)
            self.group_rotate_cw_btn.setEnabled(True)
            self.group_up_btn.setEnabled(True)
            self.group_down_btn.setEnabled(True)
            self.group_left_btn.setEnabled(True)
            self.group_right_btn.setEnabled(True)
            self.group_center_btn.setEnabled(True)
            
            # Update group info
            self.group_name_label.setText(f"Group Selection ({len(self.selected_fragment_ids)} fragments)")
            
        elif has_fragment and not self.is_group_selected:
            # Single fragment selection - enable everything
            self.transform_group.setEnabled(True)
            self.position_group.setEnabled(True)
            self.display_group.setEnabled(True)
            
            fragment = self.current_fragment
            
            # Enable all controls for single fragments
            self.angle_spinbox.setEnabled(True)
            self.angle_45_btn.setEnabled(True)
            self.angle_neg45_btn.setEnabled(True)
            self.rotate_cw_btn.setEnabled(True)
            self.rotate_ccw_btn.setEnabled(True)
            self.flip_h_btn.setEnabled(True)
            self.flip_v_btn.setEnabled(True)
            self.x_spinbox.setEnabled(True)
            self.y_spinbox.setEnabled(True)
            
            # Update info
            self.name_label.setText(fragment.name or f"Fragment {fragment.id[:8]}")
            self.size_label.setText(f"Size: {fragment.original_size[0]} × {fragment.original_size[1]}")
            self.file_label.setText(f"File: {fragment.file_path}")
            
            self.visible_checkbox.setEnabled(True)
            self.opacity_slider.setEnabled(True)
            
            # Update position controls (block signals to prevent recursion)
            self.x_spinbox.blockSignals(True)
            self.y_spinbox.blockSignals(True)
            self.x_spinbox.setValue(fragment.x)
            self.y_spinbox.setValue(fragment.y)
            self.x_spinbox.blockSignals(False)
            self.y_spinbox.blockSignals(False)
            
            # Update angle control
            self.angle_spinbox.blockSignals(True)
            self.angle_spinbox.setValue(fragment.rotation)
            self.angle_spinbox.blockSignals(False)
            
            # Update display controls
            self.visible_checkbox.blockSignals(True)
            self.visible_checkbox.setChecked(fragment.visible)
            self.visible_checkbox.blockSignals(False)
            
            self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(int(fragment.opacity * 100))
            self.opacity_label.setText(f"{int(fragment.opacity * 100)}%")
            self.opacity_slider.blockSignals(False)
            
            # Update transform button states
            self.update_transform_button_states()
            
        else:
            # No selection - disable everything
            self.transform_group.setEnabled(False)
            self.position_group.setEnabled(False)
            self.display_group.setEnabled(False)
            self.name_label.setText("No selection")
            self.size_label.setText("Size: -")
            self.file_label.setText("File: -")
        
    def update_transform_button_states(self):
        """Update the visual state of transform buttons"""
        if not self.current_fragment:
            return
            
        fragment = self.current_fragment
        
        # Update flip button styles based on current state
        if fragment.flip_horizontal:
            self.flip_h_btn.setStyleSheet("QPushButton { background-color: #4a90e2; }")
        else:
            self.flip_h_btn.setStyleSheet("")
            
        if fragment.flip_vertical:
            self.flip_v_btn.setStyleSheet("QPushButton { background-color: #4a90e2; }")
        else:
            self.flip_v_btn.setStyleSheet("")
            
    def request_transform(self, transform_type: str, value=None):
        """Request a transformation for the current fragment"""
        if self.current_fragment and not self.is_group_selected:
            # Handle single fragment transformations
            self.transform_requested.emit(self.current_fragment.id, transform_type, value)
    
    def request_group_transform(self, transform_type: str, value=None):
        """Request a transformation for the group"""
        if self.is_group_selected:
            if transform_type in ['rotate_cw', 'rotate_ccw']:
                self.transform_requested.emit('group', transform_type, self.selected_fragment_ids)
            elif transform_type == 'translate':
                self.transform_requested.emit('group', transform_type, (self.selected_fragment_ids, value))
    
    def request_group_reset(self):
        """Request reset of all group fragment transforms"""
        if self.is_group_selected:
            for fragment_id in self.selected_fragment_ids:
                self.reset_transform_requested.emit(fragment_id)
            
    def request_reset(self):
        """Request reset of current fragment transforms"""
        if self.is_group_selected:
            # Reset all fragments in group
            for fragment_id in self.selected_fragment_ids:
                self.reset_transform_requested.emit(fragment_id)
        elif self.current_fragment:
            self.reset_transform_requested.emit(self.current_fragment.id)
            
    def on_position_changed(self):
        """Handle position spinbox changes"""
        if self.current_fragment:
            new_x = self.x_spinbox.value()
            new_y = self.y_spinbox.value()
            self.request_transform('translate', (new_x - self.current_fragment.x, 
                                               new_y - self.current_fragment.y))
            
    def on_visibility_changed(self, state):
        """Handle visibility checkbox changes"""
        if self.current_fragment:
            visible = state == Qt.CheckState.Checked.value
            self.transform_requested.emit(self.current_fragment.id, 'set_visibility', visible)
            
    def on_opacity_changed(self, value):
        """Handle opacity slider changes"""
        if self.current_fragment:
            opacity = value / 100.0
            self.current_fragment.opacity = opacity
            self.opacity_label.setText(f"{value}%")
            
    def on_angle_changed(self):
        """Handle angle spinbox changes"""
        if self.current_fragment:
            new_angle = self.angle_spinbox.value()
            self.request_transform('set_rotation', new_angle)