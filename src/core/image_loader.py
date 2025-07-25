"""
Image loading utilities for various formats including pyramidal images
"""

import os
import numpy as np
from typing import Optional, Tuple
import cv2
from PIL import Image
import tifffile

try:
    import openslide
    OPENSLIDE_AVAILABLE = True
except ImportError:
    OPENSLIDE_AVAILABLE = False

class ImageLoader:
    """Handles loading of various image formats including pyramidal images"""
    
    def __init__(self):
        self.supported_formats = {'.tiff', '.tif', '.png', '.jpg', '.jpeg'}
        if OPENSLIDE_AVAILABLE:
            self.supported_formats.update({'.svs', '.ndpi', '.vms', '.vmu'})
    
    def load_image(self, file_path: str, level: int = 0) -> Optional[np.ndarray]:
        """
        Load image from file path
        
        Args:
            file_path: Path to image file
            level: Pyramid level for multi-resolution images (0 = highest resolution)
            
        Returns:
            Image data as numpy array or None if loading failed
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image file not found: {file_path}")
            
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        try:
            if file_ext == '.svs' and OPENSLIDE_AVAILABLE:
                return self._load_openslide_image(file_path, level)
            elif file_ext in {'.tiff', '.tif'}:
                return self._load_tiff_image(file_path)
            else:
                return self._load_standard_image(file_path)
                
        except Exception as e:
            raise RuntimeError(f"Failed to load image {file_path}: {str(e)}")
    
    def _load_openslide_image(self, file_path: str, level: int = 8) -> np.ndarray:
        """Load image using OpenSlide for pyramidal formats"""
        slide = openslide.OpenSlide(file_path)
        
        # Get image at specified level
        if level >= slide.level_count:
            level = slide.level_count - 1
            
        # Read the entire level
        image = slide.read_region((0, 0), level, slide.level_dimensions[level])
        
        # Keep RGBA format to preserve alpha channel
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Convert to numpy array
        image_array = np.array(image)
        
        slide.close()
        return image_array
    


    def _load_tiff_image(self, file_path: str, level: int = 7) -> np.ndarray:
        """Load TIFF image using tifffile, handling both standard and pyramidal TIFFs"""
        try:
            # Use tifffile directly for pyramidal TIFFs
            with tifffile.TiffFile(file_path) as tif:
                if hasattr(tif, 'series') and tif.series:
                    series = tif.series[0]
                    if hasattr(series, 'levels') and len(series.levels) > 1:
                        # Pyramidal TIFF
                        max_level = len(series.levels) - 1
                        if level > max_level:
                            level = max_level
                        
                        print(f"Loading pyramidal TIFF {file_path} at level {level} (max level: {max_level})")
                        
                        # Read the specific level
                        level_data = series.levels[level].asarray()
                        
                        # Convert to RGBA if needed
                        if len(level_data.shape) == 2:
                            # Grayscale to RGBA
                            rgb = np.stack([level_data] * 3, axis=2)
                            alpha = np.full(level_data.shape, 255, dtype=np.uint8)
                            image_array = np.dstack([rgb, alpha])
                        elif len(level_data.shape) == 3:
                            if level_data.shape[2] == 3:
                                # RGB to RGBA
                                alpha = np.full(level_data.shape[:2], 255, dtype=np.uint8)
                                image_array = np.dstack([level_data, alpha])
                            elif level_data.shape[2] == 4:
                                # Already RGBA
                                image_array = level_data
                            else:
                                raise ValueError(f"Unsupported number of channels: {level_data.shape[2]}")
                        else:
                            raise ValueError(f"Unsupported image dimensions: {level_data.shape}")
                        
                        return image_array
                    else:
                        # Single level TIFF
                        print(f"Loading single-level TIFF {file_path}")
                        image_data = tif.asarray()
                        
                        # Convert to RGBA if needed
                        if len(image_data.shape) == 2:
                            rgb = np.stack([image_data] * 3, axis=2)
                            alpha = np.full(image_data.shape, 255, dtype=np.uint8)
                            image_array = np.dstack([rgb, alpha])
                        elif len(image_data.shape) == 3:
                            if image_data.shape[2] == 3:
                                alpha = np.full(image_data.shape[:2], 255, dtype=np.uint8)
                                image_array = np.dstack([image_data, alpha])
                            elif image_data.shape[2] == 4:
                                image_array = image_data
                            else:
                                raise ValueError(f"Unsupported number of channels: {image_data.shape[2]}")
                        else:
                            raise ValueError(f"Unsupported image dimensions: {image_data.shape}")
                        
                        return image_array
                else:
                    raise ValueError("No series found in TIFF file")
                    
        except Exception as e:
            print(f"tifffile failed for {file_path}: {e}")
            
            # Final fallback to PIL
            try:
                image = Image.open(file_path)
                # Preserve alpha channel if present
                if image.mode in ['RGBA', 'LA']:
                    pass  # Keep as is
                elif image.mode in ['RGB', 'L']:
                    # Add alpha channel
                    image = image.convert('RGBA')
                image_array = np.array(image)
                print(f"Loaded {file_path} using PIL, shape: {image_array.shape}")
            except Exception as pil_error:
                print(f"PIL also failed for {file_path}: {pil_error}")
                raise

    
    def _load_standard_image(self, file_path: str) -> np.ndarray:
        """Load standard image formats using OpenCV"""
        # Load with alpha channel support
        image_array = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
        
        if image_array is None:
            raise ValueError(f"Could not load image: {file_path}")
            
        # Handle different channel configurations
        if len(image_array.shape) == 2:
            # Grayscale to RGBA
            rgb = np.stack([image_array] * 3, axis=2)
            alpha = np.full(image_array.shape, 255, dtype=np.uint8)
            image_array = np.dstack([rgb, alpha])
        elif len(image_array.shape) == 3:
            if image_array.shape[2] == 3:
                # BGR to RGBA
                image_array = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
                alpha = np.full(image_array.shape[:2], 255, dtype=np.uint8)
                image_array = np.dstack([image_array, alpha])
            elif image_array.shape[2] == 4:
                # BGRA to RGBA
                image_array = cv2.cvtColor(image_array, cv2.COLOR_BGRA2RGBA)
        
        return image_array
    
    def get_image_info(self, file_path: str) -> dict:
        """Get information about an image file"""
        info = {
            'file_path': file_path,
            'file_size': os.path.getsize(file_path),
            'format': os.path.splitext(file_path)[1].lower(),
            'dimensions': None,
            'levels': 1,
            'pixel_size': None
        }
        
        try:
            file_ext = info['format']
            
            if file_ext == '.svs' and OPENSLIDE_AVAILABLE:
                slide = openslide.OpenSlide(file_path)
                info['dimensions'] = slide.level_dimensions
                info['levels'] = slide.level_count
                
                # Try to get pixel size from metadata
                try:
                    mpp_x = float(slide.properties.get(openslide.PROPERTY_NAME_MPP_X, 0))
                    mpp_y = float(slide.properties.get(openslide.PROPERTY_NAME_MPP_Y, 0))
                    if mpp_x > 0 and mpp_y > 0:
                        info['pixel_size'] = (mpp_x, mpp_y)
                except:
                    pass
                    
                slide.close()
                
            else:
                image = Image.open(file_path)
                info['dimensions'] = [(image.width, image.height)]
                image.close()
                
        except Exception as e:
            print(f"Warning: Could not get info for {file_path}: {e}")
            
        return info
    
    def is_pyramidal(self, file_path: str) -> bool:
        """Check if image is pyramidal (multi-resolution)"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.svs' and OPENSLIDE_AVAILABLE:
            return True
        elif file_ext in {'.tiff', '.tif'}:
            try:
                with tifffile.TiffFile(file_path) as tif:
                    return tif.is_pyramidal
            except:
                return False
        
        return False
    
    def get_pyramid_info(self, file_path: str) -> dict:
        """Get detailed pyramid information for a file"""
        info = {
            'levels': [],
            'level_dimensions': [],
            'level_downsamples': [],
            'has_pyramid': False
        }
        
        try:
            if OPENSLIDE_AVAILABLE and self._is_openslide_compatible(file_path):
                slide = openslide.OpenSlide(file_path)
                
                info['levels'] = list(range(slide.level_count))
                info['level_dimensions'] = slide.level_dimensions
                info['level_downsamples'] = slide.level_downsamples
                info['has_pyramid'] = slide.level_count > 1
                
                slide.close()
            else:
                # Fallback to tifffile
                import tifffile
                with tifffile.TiffFile(file_path) as tif:
                    if hasattr(tif, 'series') and tif.series:
                        series = tif.series[0]
                        if hasattr(series, 'levels') and len(series.levels) > 1:
                            info['levels'] = list(range(len(series.levels)))
                            info['level_dimensions'] = [(level.shape[1], level.shape[0]) for level in series.levels]
                            info['level_downsamples'] = [1.0 * (2 ** i) for i in range(len(series.levels))]
                            info['has_pyramid'] = True
                        else:
                            # Single level
                            info['levels'] = [0]
                            info['level_dimensions'] = [(tif.pages[0].shape[1], tif.pages[0].shape[0])]
                            info['level_downsamples'] = [1.0]
                            info['has_pyramid'] = False
                    else:
                        # Single level fallback
                        info['levels'] = [0]
                        info['level_dimensions'] = [(tif.pages[0].shape[1], tif.pages[0].shape[0])]
                        info['level_downsamples'] = [1.0]
                        info['has_pyramid'] = False
                        
        except Exception as e:
            print(f"Warning: Could not get pyramid info for {file_path}: {e}")
            # Return minimal info
            info['levels'] = [0]
            info['level_dimensions'] = [(0, 0)]
            info['level_downsamples'] = [1.0]
            info['has_pyramid'] = False
            
        return info
    
    def _is_openslide_compatible(self, file_path: str) -> bool:
        """Check if file is compatible with OpenSlide"""
        if not OPENSLIDE_AVAILABLE:
            return False
            
        try:
            # Try to detect if OpenSlide can handle this file
            openslide.OpenSlide.detect_format(file_path)
            return True
        except:
            return False