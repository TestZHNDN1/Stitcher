"""
Labeled point data structure for fragment stitching
"""

from dataclasses import dataclass
from typing import Tuple
import uuid

@dataclass
class LabeledPoint:
    """Represents a labeled interest point on a fragment"""
    
    id: str
    label: str
    x: float  # Local coordinates relative to fragment
    y: float
    fragment_id: str
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'label': self.label,
            'x': self.x,
            'y': self.y,
            'fragment_id': self.fragment_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LabeledPoint':
        """Create from dictionary"""
        return cls(
            id=data.get('id', ''),
            label=data['label'],
            x=data['x'],
            y=data['y'],
            fragment_id=data['fragment_id']
        )