"""
Pyramidal TIFF exporter with transformation support
"""

import os
import numpy as np
from typing import List, Dict, Tuple, Optional, Callable
import logging
import tempfile
import shutil
import math

# Import QApplication for processEvents
from PyQt6.QtWidgets import QApplication

try:
    import openslide
    OPENSLIDE_AVAILABLE = True
except ImportError:
    OPENSLIDE_AVAILABLE = False

try:
    import tifffile
    TIFFFILE_AVAILABLE = True
except ImportError:
    TIFFFILE_AVAILABLE = False

try:
    import pyvips
    PYVIPS_AVAILABLE = True
except ImportError:
    PYVIPS_AVAILABLE = False

from ..core.fragment import Fragment

class PyramidalExporter:
    """Handles export of stitched pyramidal TIFF files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Check available libraries
        if not OPENSLIDE_AVAILABLE:
            self.logger.warning("OpenSlide not available - limited pyramid support")
        if not TIFFFILE_AVAILABLE:
            self.logger.warning("tifffile not available - limited TIFF support")
        if not PYVIPS_AVAILABLE:
            self.logger.warning("pyvips not available - using fallback methods")
            
    def export_pyramidal_tiff(self, fragments: List[Fragment], output_path: str,
                             selected_levels: List[int], compression: str = "LZW",
                             tile_size: int = 256, progress_callback: Optional[Callable] = None) -> bool:
        """
        Export fragments as a stitched pyramidal TIFF
        
        Args:
            fragments: List of visible Fragment objects
            output_path: Output file path
            selected_levels: List of pyramid levels to export
            compression: Compression method ("LZW", "JPEG", "Deflate", "None")
            tile_size: Tile size for pyramid (default 256)
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            self.logger.info(f"Starting pyramidal TIFF export to {output_path}")
            
            # Filter visible fragments with source files
            visible_fragments = [f for f in fragments if f.visible and f.file_path and os.path.exists(f.file_path)]
            if not visible_fragments:
                raise ValueError("No visible fragments with valid source files to export")
            
            # Validate selected levels
            if not selected_levels:
                raise ValueError("No pyramid levels selected for export")
                
            # Use fallback method (more reliable for our use case)
            return self._export_with_fallback(
                visible_fragments, output_path, selected_levels,
                compression, progress_callback
            )
                
        except Exception as e:
            self.logger.error(f"Pyramidal TIFF export failed: {str(e)}")
            if progress_callback:
                progress_callback(0, f"Export failed: {str(e)}")
            return False
            
    def _export_with_fallback(self, fragments: List[Fragment], output_path: str,
                             selected_levels: List[int], compression: str,
                             progress_callback: Optional[Callable]) -> bool:
        """Fallback export method using tifffile and numpy"""
        try:
            if not TIFFFILE_AVAILABLE:
                raise ImportError("tifffile required for fallback export")
            
            # Process each level
            level_images = {}
            total_levels = len(selected_levels)
            
            for i, level in enumerate(selected_levels):
                if progress_callback:
                    progress = int((i / total_levels) * 90)
                    progress_callback(progress, f"Processing level {level}")
                    QApplication.processEvents()  # Allow UI updates
                
                try:
                    # Calculate bounds for this level
                    bounds = self._calculate_composite_bounds_at_level(fragments, level)
                    if not bounds:
                        self.logger.warning(f"Could not calculate bounds for level {level}")
                        continue
                        
                    # Render composite for this level
                    composite = self._render_composite_at_level(fragments, level, bounds)
                    if composite is not None:
                        level_images[level] = composite
                        self.logger.info(f"Successfully processed level {level}, size: {composite.shape}")
                    else:
                        self.logger.warning(f"Failed to render composite for level {level}")
                        
                except Exception as e:
                    self.logger.error(f"Error processing level {level}: {str(e)}")
                    continue
            
            if not level_images:
                raise ValueError("No levels could be processed successfully")
            
            # Save as multi-page TIFF
            if progress_callback:
                progress_callback(95, "Saving TIFF file...")
                QApplication.processEvents()
            
            # Configure compression
            compression_map = {
                "LZW": "lzw",
                "JPEG": "jpeg",
                "Deflate": "zlib", 
                "None": None
            }
            tiff_compression = compression_map.get(compression)
            
            # Prepare pages in level order (highest resolution first)
            pages = []
            self.logger.info(f"Preparing {len(level_images)} pages for TIFF")
            for level in sorted(level_images.keys()):
                image = level_images[level]
                self.logger.info(f"Level {level} image shape: {image.shape}")
                # Convert RGBA to RGB if needed for JPEG compression
                if tiff_compression == "jpeg" and image.shape[2] == 4:
                    # Convert RGBA to RGB with white background
                    rgb_image = self._rgba_to_rgb(image)
                    pages.append(rgb_image)
                else:
                    pages.append(image)
            
            if not pages:
                raise ValueError("No valid pages to save")
                
            # Save with appropriate options
            save_kwargs = {
                'compression': tiff_compression,
                'photometric': 'rgb',
                'metadata': {'axes': 'YXC'}
            }
            
            # Add tiling only if compression supports it
            if tiff_compression in ['lzw', 'zlib', None]:
                save_kwargs['tile'] = (256, 256)
            
            # Remove None values
            save_kwargs = {k: v for k, v in save_kwargs.items() if v is not None}
            
            # Save each page separately to avoid shape issues
            if len(pages) == 1:
                # Single page
                tifffile.imwrite(output_path, pages[0], **save_kwargs)
            else:
                # Multi-page TIFF - save as separate pages
                with tifffile.TiffWriter(output_path) as tiff_writer:
                    for i, page in enumerate(pages):
                        page_kwargs = save_kwargs.copy()
                        if i == 0:
                            # First page can have metadata
                            pass
                        else:
                            # Subsequent pages should not repeat metadata
                            page_kwargs.pop('metadata', None)
                        
                        tiff_writer.write(page, **page_kwargs)
            
            if progress_callback:
                progress_callback(100, "Export complete")
                QApplication.processEvents()
                
            self.logger.info(f"Pyramidal TIFF export completed successfully with {len(pages)} levels")
            return True
            
        except Exception as e:
            self.logger.error(f"Fallback export failed: {str(e)}")
            if progress_callback:
                progress_callback(0, f"Export failed: {str(e)}")
            return False
            
    def _calculate_composite_bounds_at_level(self, fragments: List[Fragment], level: int) -> Optional[Tuple[float, float, float, float]]:
        """Calculate composite bounds at a specific pyramid level"""
        if not fragments:
            return None
            
        # Calculate bounds using the current fragment positions (which are at level 0 scale)
        # Then scale appropriately for the target level
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for fragment in fragments:
            # Load the fragment at the target level to get actual dimensions
            try:
                fragment_image = self._load_and_transform_fragment(fragment, level)
                if fragment_image is None:
                    continue
                    
                frag_h, frag_w = fragment_image.shape[:2]
                
                # Scale fragment position for this level
                downsample = 2 ** level
                scaled_x = fragment.x / downsample
                scaled_y = fragment.y / downsample
                
                min_x = min(min_x, scaled_x)
                min_y = min(min_y, scaled_y)
                max_x = max(max_x, scaled_x + frag_w)
                max_y = max(max_y, scaled_y + frag_h)
                
            except Exception as e:
                self.logger.warning(f"Could not get bounds for fragment {fragment.name} at level {level}: {e}")
                continue
            
        if min_x == float('inf'):
            return None
            
        scaled_bounds = (min_x, min_y, max_x, max_y)
        
        self.logger.info(f"Level {level} bounds: {scaled_bounds}")
        return scaled_bounds
        
    def _render_composite_at_level(self, fragments: List[Fragment], level: int,
                                  bounds: Tuple[float, float, float, float]) -> Optional[np.ndarray]:
        """Render composite image at specific pyramid level using numpy"""
        try:
            min_x, min_y, max_x, max_y = bounds
            width = int(max_x - min_x)
            height = int(max_y - min_y)
            
            if width <= 0 or height <= 0:
                self.logger.warning(f"Invalid dimensions for level {level}: {width}x{height}")
                return None
            
            self.logger.info(f"Rendering level {level} composite: {width}x{height}")
            
            # Create composite array with alpha channel
            composite = np.zeros((height, width, 4), dtype=np.uint8)
            
            # Render each fragment
            for fragment in fragments:
                try:
                    # Load fragment at the specified pyramid level
                    fragment_image = self._load_and_transform_fragment(fragment, level)
                    if fragment_image is None:
                        self.logger.warning(f"Could not load fragment {fragment.name} at level {level}")
                        continue
                    
                    self._composite_fragment_numpy(composite, fragment_image, fragment, bounds, level)
                    self.logger.debug(f"Composited fragment {fragment.name} at level {level}")
                    
                except Exception as e:
                    self.logger.error(f"Error compositing fragment {fragment.name} at level {level}: {str(e)}")
                    continue
            
            return composite
            
        except Exception as e:
            self.logger.error(f"Failed to render composite at level {level}: {str(e)}")
            return None
            
    def _load_and_transform_fragment(self, fragment: Fragment, level: int) -> Optional[np.ndarray]:
        """Load fragment at specific level and apply transformations"""
        try:
            # Load fragment at the specified pyramid level using tifffile
            from ..core.image_loader import ImageLoader
            loader = ImageLoader()
            
            # Load at the specified level - tifffile will handle pyramid levels properly
            original_image = loader.load_image(fragment.file_path, level)
            if original_image is None:
                return None
            
            # Apply transformations (rotation, flip) to the loaded image
            # Note: Position transformations are handled during compositing
            transformed_image = self._apply_image_transforms(original_image, fragment)
            
            return transformed_image
            
        except Exception as e:
            self.logger.error(f"Failed to load fragment {fragment.name} at level {level}: {str(e)}")
            return None
            
    def _apply_image_transforms(self, image: np.ndarray, fragment: Fragment) -> np.ndarray:
        """Apply rotation and flip transformations to image"""
        import cv2
        
        result = image.copy()
        
        # Apply horizontal flip
        if fragment.flip_horizontal:
            result = np.fliplr(result)
            
        # Apply vertical flip  
        if fragment.flip_vertical:
            result = np.flipud(result)
            
        # Apply rotation
        if abs(fragment.rotation) > 0.01:
            result = self._rotate_image(result, fragment.rotation)
            
        return result
        
    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by arbitrary angle"""
        import cv2
        
        if abs(angle) < 0.01:
            return image
            
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        
        # Get rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Calculate new bounding box
        cos_val = abs(rotation_matrix[0, 0])
        sin_val = abs(rotation_matrix[0, 1])
        new_width = int((height * sin_val) + (width * cos_val))
        new_height = int((height * cos_val) + (width * sin_val))
        
        # Adjust rotation matrix for new center
        rotation_matrix[0, 2] += (new_width / 2) - center[0]
        rotation_matrix[1, 2] += (new_height / 2) - center[1]
        
        # Apply rotation
        if len(image.shape) == 3 and image.shape[2] == 4:
            # Handle RGBA
            rotated = cv2.warpAffine(
                image, rotation_matrix, (new_width, new_height),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0, 0)
            )
        else:
            rotated = cv2.warpAffine(
                image, rotation_matrix, (new_width, new_height),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0)
            )
            
        return rotated
            
    def _composite_fragment_numpy(self, composite: np.ndarray, fragment_image: np.ndarray,
                                 fragment: Fragment, bounds: Tuple[float, float, float, float], level: int):
        """Composite fragment onto composite array using numpy"""
        try:
            min_x, min_y, _, _ = bounds
            downsample = 2 ** level
            
            # Calculate position in composite
            # Fragment positions are at level 0 scale, so we need to scale them down
            scaled_frag_x = fragment.x / downsample
            scaled_frag_y = fragment.y / downsample
            
            frag_x = int(scaled_frag_x - min_x)
            frag_y = int(scaled_frag_y - min_y)
            
            # Get dimensions
            frag_h, frag_w = fragment_image.shape[:2]
            comp_h, comp_w = composite.shape[:2]
            
            # Calculate intersection
            src_x1 = max(0, -frag_x)
            src_y1 = max(0, -frag_y)
            src_x2 = min(frag_w, comp_w - frag_x)
            src_y2 = min(frag_h, comp_h - frag_y)
            
            dst_x1 = max(0, frag_x)
            dst_y1 = max(0, frag_y)
            dst_x2 = dst_x1 + (src_x2 - src_x1)
            dst_y2 = dst_y1 + (src_y2 - src_y1)
            
            # Check overlap
            if src_x2 <= src_x1 or src_y2 <= src_y1:
                return
                
            # Extract regions
            fragment_region = fragment_image[src_y1:src_y2, src_x1:src_x2]
            
            # Ensure fragment region has alpha channel
            if len(fragment_region.shape) == 3 and fragment_region.shape[2] == 3:
                # Add alpha channel
                alpha_channel = np.full(fragment_region.shape[:2] + (1,), 255, dtype=np.uint8)
                fragment_region = np.concatenate([fragment_region, alpha_channel], axis=2)
            
            # Alpha blending
            if fragment_region.shape[2] == 4:  # RGBA
                frag_alpha = fragment_region[:, :, 3:4] / 255.0 * fragment.opacity
                frag_rgb = fragment_region[:, :, :3].astype(np.float32)
                
                comp_region = composite[dst_y1:dst_y2, dst_x1:dst_x2]
                comp_alpha = comp_region[:, :, 3:4] / 255.0
                comp_rgb = comp_region[:, :, :3].astype(np.float32)
                
                # Alpha blending formula
                out_alpha = frag_alpha + (1 - frag_alpha) * comp_alpha
                
                # Avoid division by zero
                mask = out_alpha[:, :, 0] > 0
                out_rgb = np.zeros_like(frag_rgb)
                
                if np.any(mask):
                    out_rgb[mask, :] = (frag_alpha[mask, :] * frag_rgb[mask, :] + 
                                       (1 - frag_alpha[mask, :]) * comp_rgb[mask, :]) / out_alpha[mask, :]
                
                # Update composite
                composite[dst_y1:dst_y2, dst_x1:dst_x2, :3] = np.clip(out_rgb, 0, 255).astype(np.uint8)
                composite[dst_y1:dst_y2, dst_x1:dst_x2, 3:4] = np.clip(out_alpha * 255, 0, 255).astype(np.uint8)
            else:
                # RGB fallback
                alpha = fragment.opacity
                composite[dst_y1:dst_y2, dst_x1:dst_x2, :3] = (
                    alpha * fragment_region + 
                    (1 - alpha) * composite[dst_y1:dst_y2, dst_x1:dst_x2, :3]
                ).astype(np.uint8)
                composite[dst_y1:dst_y2, dst_x1:dst_x2, 3] = 255
                
        except Exception as e:
            self.logger.error(f"Failed to composite fragment: {str(e)}")
            
    def _rgba_to_rgb(self, rgba_image: np.ndarray, background_color=(255, 255, 255)) -> np.ndarray:
        """Convert RGBA image to RGB with specified background color"""
        if rgba_image.shape[2] != 4:
            return rgba_image[:, :, :3]  # Already RGB
            
        rgb = rgba_image[:, :, :3].astype(np.float32)
        alpha = rgba_image[:, :, 3:4].astype(np.float32) / 255.0
        
        # Create background
        background = np.full_like(rgb, background_color, dtype=np.float32)
        
        # Alpha blend with background
        result = (alpha * rgb + (1 - alpha) * background).astype(np.uint8)
        
        return result