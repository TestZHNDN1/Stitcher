"""
Fragment management system
"""

from typing import Dict, List, Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal
import numpy as np
import math

from .fragment import Fragment

class FragmentManager(QObject):
    """Manages all tissue fragments and their transformations"""
    
    fragments_changed = pyqtSignal()
    fragment_selected = pyqtSignal(str)  # fragment_id
    group_selection_changed = pyqtSignal(list)  # list of fragment_ids
    
    def __init__(self):
        super().__init__()
        self._fragments: Dict[str, Fragment] = {}
        self._selected_fragment_id: Optional[str] = None
        self._selected_fragment_ids: List[str] = []  # For group selection
        
    def add_fragment_from_image(self, image_data: np.ndarray, name: str, 
                               file_path: str = "") -> str:
        """Add a new fragment from image data"""
        print(f"This is the file path: {file_path}")
        fragment = Fragment(
            name=name,
            image_data=image_data,
            file_path=file_path
        )
        
        self._fragments[fragment.id] = fragment
        
        # Auto-select first fragment
        if len(self._fragments) == 1:
            self.set_selected_fragment(fragment.id)
            
        self.fragments_changed.emit()
        return fragment.id
    
    def get_fragment(self, fragment_id: str) -> Optional[Fragment]:
        """Get fragment by ID"""
        return self._fragments.get(fragment_id)
    
    def get_all_fragments(self) -> List[Fragment]:
        """Get all fragments"""
        return list(self._fragments.values())
    
    def get_selected_fragments(self) -> List[Fragment]:
        """Get all selected fragments (for group operations)"""
        return [self._fragments[fid] for fid in self._selected_fragment_ids if fid in self._fragments]
    
    def has_group_selection(self) -> bool:
        """Check if multiple fragments are selected"""
        return len(self._selected_fragment_ids) > 1
    
    def get_visible_fragments(self) -> List[Fragment]:
        """Get only visible fragments"""
        return [f for f in self._fragments.values() if f.visible]
    
    def remove_fragment(self, fragment_id: str) -> bool:
        """Remove a fragment"""
        if fragment_id in self._fragments:
            del self._fragments[fragment_id]
            
            # Update selection if removed fragment was selected
            if self._selected_fragment_id == fragment_id:
                remaining_ids = list(self._fragments.keys())
                self._selected_fragment_id = remaining_ids[0] if remaining_ids else None
                
            self.fragments_changed.emit()
            return True
        return False
    
    def set_group_selection(self, fragment_ids: List[str]):
        """Set multiple fragments as selected (group selection)"""
        # Clear previous selections
        for fid in self._selected_fragment_ids:
            fragment = self._fragments.get(fid)
            if fragment:
                fragment.selected = False
        
        # Clear single selection
        if self._selected_fragment_id:
            prev_fragment = self._fragments.get(self._selected_fragment_id)
            if prev_fragment:
                prev_fragment.selected = False
        
        # Set new group selection
        self._selected_fragment_ids = [fid for fid in fragment_ids if fid in self._fragments]
        self._selected_fragment_id = None  # Clear single selection when group is selected
        
        # Mark fragments as selected
        for fid in self._selected_fragment_ids:
            fragment = self._fragments.get(fid)
            if fragment:
                fragment.selected = True
        
        self.group_selection_changed.emit(self._selected_fragment_ids)
        self.fragments_changed.emit()
    
    def clear_selection(self):
        """Clear all selections"""
        # Clear group selection
        for fid in self._selected_fragment_ids:
            fragment = self._fragments.get(fid)
            if fragment:
                fragment.selected = False
        
        # Clear single selection
        if self._selected_fragment_id:
            fragment = self._fragments.get(self._selected_fragment_id)
            if fragment:
                fragment.selected = False
        
        self._selected_fragment_ids = []
        self._selected_fragment_id = None
        
        self.group_selection_changed.emit([])
        self.fragments_changed.emit()
    
    def set_selected_fragment(self, fragment_id: Optional[str]):
        """Set the selected fragment"""
        # Clear group selection when selecting single fragment
        for fid in self._selected_fragment_ids:
            fragment = self._fragments.get(fid)
            if fragment:
                fragment.selected = False
        self._selected_fragment_ids = []
        
        # Deselect previous fragment
        if self._selected_fragment_id:
            prev_fragment = self._fragments.get(self._selected_fragment_id)
            if prev_fragment:
                prev_fragment.selected = False
                
        self._selected_fragment_id = fragment_id
        
        # Select new fragment
        if fragment_id and fragment_id in self._fragments:
            self._fragments[fragment_id].selected = True
            self.fragment_selected.emit(fragment_id)
        
        self.group_selection_changed.emit(self._selected_fragment_ids)
            
        self.fragments_changed.emit()
    
    def get_selected_fragment_id(self) -> Optional[str]:
        """Get the selected fragment ID"""
        return self._selected_fragment_id
    
    def get_selected_fragment_ids(self) -> List[str]:
        """Get all selected fragment IDs (including group selection)"""
        if self._selected_fragment_ids:
            return self._selected_fragment_ids.copy()
        return [self._selected_fragment_id] if self._selected_fragment_id else []
    
    def get_selected_fragment(self) -> Optional[Fragment]:
        """Get the selected fragment"""
        if self._selected_fragment_id:
            return self._fragments.get(self._selected_fragment_id)
        return None
    
    def set_fragment_visibility(self, fragment_id: str, visible: bool):
        """Set fragment visibility"""
        fragment = self._fragments.get(fragment_id)
        if fragment:
            fragment.visible = visible
            self.fragments_changed.emit()
    
    def set_fragment_position(self, fragment_id: str, x: float, y: float):
        """Set fragment position"""
        fragment = self._fragments.get(fragment_id)
        if fragment:
            # Store positions as floats without excessive rounding
            fragment.x = float(x)
            fragment.y = float(y)
            
            self.fragments_changed.emit()
    
    def translate_fragment(self, fragment_id: str, dx: float, dy: float):
        """Translate fragment by offset"""
        fragment = self._fragments.get(fragment_id)
        if fragment:
            fragment.x = fragment.x + float(dx)
            fragment.y = fragment.y + float(dy)
            
            self.fragments_changed.emit()
    
    def translate_group(self, fragment_ids: List[str], dx: float, dy: float):
        """Translate multiple fragments by the same offset (preserving relative positions)"""
        for fragment_id in fragment_ids:
            fragment = self._fragments.get(fragment_id)
            if fragment:
                fragment.x = fragment.x + float(dx)
                fragment.y = fragment.y + float(dy)
        
        self.fragments_changed.emit()
    
    def rotate_fragment(self, fragment_id: str, angle: int):
        """Rotate fragment by angle (90 degree increments)"""
        fragment = self._fragments.get(fragment_id)
        if fragment:
            fragment.rotation = (fragment.rotation + angle) % 360.0
            fragment.invalidate_cache()
            self.fragments_changed.emit()
    
    def set_fragment_rotation(self, fragment_id: str, angle: float):
        """Set fragment rotation to specific angle"""
        fragment = self._fragments.get(fragment_id)
        if fragment:
            fragment.rotation = angle % 360.0
            fragment.invalidate_cache()
            self.fragments_changed.emit()
    
    def rotate_group(self, fragment_ids: List[str], angle: int):
        """Rotate multiple fragments around their group center"""
        print(f"rotate_group called with {len(fragment_ids)} fragments, angle: {angle}")
        if not fragment_ids:
            return
        
        # Get fragments
        fragments = [self._fragments[fid] for fid in fragment_ids if fid in self._fragments]
        if not fragments:
            print("No valid fragments found!")
            return
        
        print(f"Found {len(fragments)} valid fragments to rotate")
        
        # Calculate group center (centroid) using fragment positions, not bounding boxes
        center_x = sum(f.x for f in fragments) / len(fragments)
        center_y = sum(f.y for f in fragments) / len(fragments)
        print(f"Group center: ({center_x}, {center_y})")
        
        # Convert angle to radians
        angle_rad = math.radians(angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        # Rotate each fragment around the group center
        for fragment in fragments:
            # Translate fragment position to origin (relative to group center)
            rel_x = fragment.x - center_x
            rel_y = fragment.y - center_y
            
            # Rotate around origin
            new_rel_x = rel_x * cos_a - rel_y * sin_a
            new_rel_y = rel_x * sin_a + rel_y * cos_a
            
            # Translate back to world coordinates
            fragment.x = center_x + new_rel_x
            fragment.y = center_y + new_rel_y
            
            # Also rotate the fragment itself
            fragment.rotation = (fragment.rotation + angle) % 360.0
            fragment.invalidate_cache()
            print(f"Rotated fragment {fragment.name}: new pos=({fragment.x:.1f}, {fragment.y:.1f}), new rotation={fragment.rotation}")
        
        print("Group rotation completed, emitting fragments_changed")
        self.fragments_changed.emit()
    
    def flip_fragment(self, fragment_id: str, horizontal: bool = True):
        """Flip fragment horizontally or vertically"""
        fragment = self._fragments.get(fragment_id)
        if fragment:
            if horizontal:
                fragment.flip_horizontal = not fragment.flip_horizontal
            else:
                fragment.flip_vertical = not fragment.flip_vertical
            fragment.invalidate_cache()
            self.fragments_changed.emit()
    
    def set_fragment_transform(self, fragment_id: str, rotation: int = None,
                              translation: Tuple[float, float] = None,
                              flip_horizontal: bool = None,
                              flip_vertical: bool = None):
        """Set complete fragment transformation"""
        fragment = self._fragments.get(fragment_id)
        if fragment:
            transform_changed = False
            if rotation is not None:
                fragment.rotation = float(rotation) % 360.0
                transform_changed = True
            if translation is not None:
                fragment.x = float(translation[0])
                fragment.y = float(translation[1])
            if flip_horizontal is not None:
                fragment.flip_horizontal = flip_horizontal
                transform_changed = True
            if flip_vertical is not None:
                fragment.flip_vertical = flip_vertical
                transform_changed = True
            # Only invalidate cache when transforms that affect the image are changed
            if transform_changed:
                fragment.invalidate_cache()
            self.fragments_changed.emit()
    
    def reset_fragment_transform(self, fragment_id: str):
        """Reset fragment transformation to default"""
        fragment = self._fragments.get(fragment_id)
        if fragment:
            fragment.reset_transform()
            self.fragments_changed.emit()
    
    def reset_all_transforms(self):
        """Reset all fragment transformations"""
        for fragment in self._fragments.values():
            fragment.reset_transform()
        self.fragments_changed.emit()
    
    def get_composite_bounds(self) -> Tuple[float, float, float, float]:
        """Get bounding box of all visible fragments (min_x, min_y, max_x, max_y)"""
        if not self._fragments:
            return (0, 0, 0, 0)
            
        visible_fragments = self.get_visible_fragments()
        if not visible_fragments:
            return (0, 0, 0, 0)
            
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for fragment in visible_fragments:
            bbox_x, bbox_y, bbox_w, bbox_h = fragment.get_bounding_box()
            min_x = min(min_x, bbox_x)
            min_y = min(min_y, bbox_y)
            max_x = max(max_x, bbox_x + bbox_w)
            max_y = max(max_y, bbox_y + bbox_h)
            
        return (min_x, min_y, max_x, max_y)
    
    def export_metadata(self) -> dict:
        """Export fragment metadata for serialization"""
        return {
            'fragments': [fragment.to_dict() for fragment in self._fragments.values()],
            'selected_fragment_id': self._selected_fragment_id,
            'version': '1.0'
        }
    
    def import_metadata(self, metadata: dict):
        """Import fragment metadata"""
        self._fragments.clear()
        
        for fragment_data in metadata.get('fragments', []):
            fragment = Fragment.from_dict(fragment_data)
            self._fragments[fragment.id] = fragment
            
        selected_id = metadata.get('selected_fragment_id')
        if selected_id and selected_id in self._fragments:
            self.set_selected_fragment(selected_id)
            
        self.fragments_changed.emit()