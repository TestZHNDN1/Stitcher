"""
Manager for labeled points and point-based stitching
"""

from typing import Dict, List, Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal
import numpy as np
import math

from .labeled_point import LabeledPoint
from .fragment import Fragment

class PointManager(QObject):
    """Manages labeled points and performs point-based stitching"""
    
    points_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._points: Dict[str, LabeledPoint] = {}  # point_id -> LabeledPoint
        self._fragment_points: Dict[str, List[str]] = {}  # fragment_id -> [point_ids]
        
    def add_point(self, fragment_id: str, label: str, x: float, y: float) -> str:
        """Add a labeled point to a fragment"""
        # Check if this fragment already has a point with this label
        existing_points = self.get_fragment_points(fragment_id)
        for point in existing_points:
            if point.label == label:
                # Update existing point position
                point.x = x
                point.y = y
                self.points_changed.emit()
                return point.id
        
        # Create new point
        point = LabeledPoint(
            id="",  # Will be auto-generated
            label=label,
            x=x,
            y=y,
            fragment_id=fragment_id
        )
        
        self._points[point.id] = point
        
        # Add to fragment's point list
        if fragment_id not in self._fragment_points:
            self._fragment_points[fragment_id] = []
        self._fragment_points[fragment_id].append(point.id)
        
        self.points_changed.emit()
        return point.id
    
    def remove_point(self, point_id: str):
        """Remove a labeled point"""
        if point_id in self._points:
            point = self._points[point_id]
            fragment_id = point.fragment_id
            
            # Remove from points dict
            del self._points[point_id]
            
            # Remove from fragment's point list
            if fragment_id in self._fragment_points:
                if point_id in self._fragment_points[fragment_id]:
                    self._fragment_points[fragment_id].remove(point_id)
                    
                # Clean up empty fragment entries
                if not self._fragment_points[fragment_id]:
                    del self._fragment_points[fragment_id]
            
            self.points_changed.emit()
    
    def get_fragment_points(self, fragment_id: str) -> List[LabeledPoint]:
        """Get all points for a fragment"""
        if fragment_id not in self._fragment_points:
            return []
        
        points = []
        for point_id in self._fragment_points[fragment_id]:
            if point_id in self._points:
                points.append(self._points[point_id])
        
        return points
    
    def get_all_points(self) -> List[LabeledPoint]:
        """Get all labeled points"""
        return list(self._points.values())
    
    def get_points_by_label(self, label: str) -> List[LabeledPoint]:
        """Get all points with a specific label"""
        return [point for point in self._points.values() if point.label == label]
    
    def get_matching_labels(self) -> Dict[str, List[str]]:
        """Get labels that appear on exactly two fragments"""
        label_fragments = {}  # label -> [fragment_ids]
        
        for point in self._points.values():
            if point.label not in label_fragments:
                label_fragments[point.label] = []
            if point.fragment_id not in label_fragments[point.label]:
                label_fragments[point.label].append(point.fragment_id)
        
        # Return only labels that appear on exactly 2 fragments
        matching_labels = {}
        for label, fragment_ids in label_fragments.items():
            if len(fragment_ids) == 2:
                matching_labels[label] = fragment_ids
        
        return matching_labels
    
    def stitch_fragments_by_labels(self, fragments: List[Fragment]) -> Dict[str, dict]:
        """
        Perform stitching based on matching labeled points
        Returns dictionary of fragment transforms to apply
        """
        matching_labels = self.get_matching_labels()
        
        if not matching_labels:
            return {}
        
        transforms = {}
        processed_pairs = set()
        
        for label, fragment_ids in matching_labels.items():
            if len(fragment_ids) != 2:
                continue
                
            frag1_id, frag2_id = fragment_ids
            pair_key = tuple(sorted([frag1_id, frag2_id]))
            
            if pair_key in processed_pairs:
                continue
                
            processed_pairs.add(pair_key)
            
            # Get fragments
            frag1 = next((f for f in fragments if f.id == frag1_id), None)
            frag2 = next((f for f in fragments if f.id == frag2_id), None)
            
            if not frag1 or not frag2:
                continue
            
            # Get all matching points between these fragments
            frag1_points = self.get_fragment_points(frag1_id)
            frag2_points = self.get_fragment_points(frag2_id)
            
            # Find all labels that both fragments share
            frag1_labels = {p.label for p in frag1_points}
            frag2_labels = {p.label for p in frag2_points}
            shared_labels = frag1_labels.intersection(frag2_labels)
            
            if not shared_labels:
                continue
            
            # Collect matching point pairs
            point_pairs = []
            for shared_label in shared_labels:
                p1 = next((p for p in frag1_points if p.label == shared_label), None)
                p2 = next((p for p in frag2_points if p.label == shared_label), None)
                
                if p1 and p2:
                    # Convert to world coordinates
                    world_p1 = self.local_to_world(p1, frag1)
                    world_p2 = self.local_to_world(p2, frag2)
                    point_pairs.append((world_p1, world_p2))
            
            if not point_pairs:
                continue
            
            # Compute transformation (use frag1 as reference, transform frag2)
            transform = self.compute_alignment_transform(point_pairs)
            
            if transform:
                transforms[frag2_id] = transform
        
        return transforms
    
    def local_to_world(self, point: LabeledPoint, fragment: Fragment) -> Tuple[float, float]:
        """Convert point from fragment local coordinates to world coordinates"""
        # Apply fragment's current transformation to the point
        x, y = point.x, point.y
        
        # Apply rotation
        if abs(fragment.rotation) > 0.01:
            angle_rad = math.radians(fragment.rotation)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            
            x_rot = x * cos_a - y * sin_a
            y_rot = x * sin_a + y * cos_a
            x, y = x_rot, y_rot
        
        # Apply flips
        if fragment.flip_horizontal:
            x = -x
        if fragment.flip_vertical:
            y = -y
        
        # Apply translation
        world_x = x + fragment.x
        world_y = y + fragment.y
        
        return (world_x, world_y)
    
    def compute_alignment_transform(self, point_pairs: List[Tuple[Tuple[float, float], Tuple[float, float]]]) -> Optional[dict]:
        """
        Compute transformation to align point pairs
        point_pairs: [(ref_point, target_point), ...]
        Returns transform to apply to target fragment
        """
        if not point_pairs:
            return None
        
        if len(point_pairs) == 1:
            # Single point - only translation
            ref_point, target_point = point_pairs[0]
            dx = ref_point[0] - target_point[0]
            dy = ref_point[1] - target_point[1]
            
            return {
                'translation': (dx, dy),
                'rotation': 0.0
            }
        
        # Multiple points - compute rigid transformation using least squares
        ref_points = np.array([pair[0] for pair in point_pairs])
        target_points = np.array([pair[1] for pair in point_pairs])
        
        # Center the points
        ref_centroid = np.mean(ref_points, axis=0)
        target_centroid = np.mean(target_points, axis=0)
        
        ref_centered = ref_points - ref_centroid
        target_centered = target_points - target_centroid
        
        # Compute rotation using SVD
        H = target_centered.T @ ref_centered
        U, S, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T
        
        # Ensure proper rotation (det(R) = 1)
        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T @ U.T
        
        # Extract rotation angle
        rotation_angle = math.degrees(math.atan2(R[1, 0], R[0, 0]))
        
        # Compute translation
        rotated_target_centroid = R @ target_centroid
        translation = ref_centroid - rotated_target_centroid
        
        return {
            'translation': (float(translation[0]), float(translation[1])),
            'rotation': float(rotation_angle)
        }
    
    def clear_fragment_points(self, fragment_id: str):
        """Clear all points for a fragment"""
        if fragment_id in self._fragment_points:
            point_ids = self._fragment_points[fragment_id].copy()
            for point_id in point_ids:
                self.remove_point(point_id)
    
    def clear_all_points(self):
        """Clear all points"""
        self._points.clear()
        self._fragment_points.clear()
        self.points_changed.emit()
    
    def export_points(self) -> dict:
        """Export points for serialization"""
        return {
            'points': [point.to_dict() for point in self._points.values()],
            'version': '1.0'
        }
    
    def import_points(self, data: dict):
        """Import points from serialization"""
        self.clear_all_points()
        
        for point_data in data.get('points', []):
            point = LabeledPoint.from_dict(point_data)
            self._points[point.id] = point
            
            # Add to fragment's point list
            fragment_id = point.fragment_id
            if fragment_id not in self._fragment_points:
                self._fragment_points[fragment_id] = []
            self._fragment_points[fragment_id].append(point.id)
        
        self.points_changed.emit()