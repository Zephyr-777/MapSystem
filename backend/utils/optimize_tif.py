#!/usr/bin/env python3
"""
GDAL utility for optimizing TIF image previews
Creates compressed PNG/JPG thumbnails for web display
"""

import logging
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
import numpy as np
import rasterio

try:
    from osgeo import gdal
except ImportError:  # pragma: no cover - optional dependency
    gdal = None

logger = logging.getLogger(__name__)

def get_optimal_size(image_path: Path, target_size: Tuple[int, int] = (800, 600)) -> Tuple[int, int]:
    """
    Calculate optimal downsampling size based on original dimensions
    """
    try:
        with Image.open(image_path) as img:
            orig_width, orig_height = img.size

            # Calculate scaling factor to fit within target size
            scale_w = target_size[0] / orig_width
            scale_h = target_size[1] / orig_height
            scale = min(scale_w, scale_h)

            # Calculate new dimensions maintaining aspect ratio
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)

            # Ensure minimum size
            new_width = max(new_width, 400)
            new_height = max(new_height, 300)

            return (new_width, new_height)
    except Exception as e:
        logger.warning(f"Could not get image dimensions for {image_path}: {e}")
        return target_size

def create_web_preview(
    tif_path: Path,
    output_dir: Path,
    target_size: Tuple[int, int] = (800, 600),
) -> Optional[str]:
    """
    Create optimized web preview for TIF image

    Args:
        tif_path: Path to TIF file
        output_dir: Directory to save preview images

    Returns:
        Path to preview image, or None if failed
    """
    try:
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate preview filename
        preview_name = f"{tif_path.stem}_preview.jpg"
        preview_path = output_dir / preview_name

        # Create preview in temporary location first
        temp_preview = output_dir / f"temp_{preview_name}"

        # Method 1: Prefer GDAL for proper raster scaling and export
        try:
            if gdal is None:
                raise RuntimeError("GDAL Python bindings are not installed")

            dataset = gdal.Open(str(tif_path))
            if dataset is None:
                raise RuntimeError(f"Unable to open raster: {tif_path}")

            width, height = get_optimal_size(tif_path, target_size=target_size)
            translate_options = gdal.TranslateOptions(
                format="JPEG",
                width=width,
                height=height,
                creationOptions=["QUALITY=85", "PROGRESSIVE=ON"],
            )
            translated = gdal.Translate(str(temp_preview), dataset, options=translate_options)
            if translated is None:
                raise RuntimeError("gdal.Translate returned no dataset")
            translated = None
            dataset = None
            logger.info("Created GDAL preview: %s", temp_preview)

        except Exception as gdal_error:
            logger.warning("GDAL method failed for %s: %s; trying rasterio/PIL fallback", tif_path, gdal_error)

            # Method 2: Use rasterio to normalize bands and generate preview
            try:
                with rasterio.open(tif_path) as src:
                    target_width, target_height = get_optimal_size(tif_path, target_size=target_size)

                    if src.count >= 3:
                        data = src.read([1, 2, 3], out_shape=(3, target_height, target_width))
                        data = np.moveaxis(data, 0, -1)
                    else:
                        data = src.read(1, out_shape=(target_height, target_width))
                        data = np.stack([data, data, data], axis=-1)

                    data = data.astype("float32")
                    finite_mask = np.isfinite(data)
                    if finite_mask.any():
                        valid_values = data[finite_mask]
                        data_min = float(valid_values.min())
                        data_max = float(valid_values.max())
                        if data_max > data_min:
                            data = (data - data_min) / (data_max - data_min)
                        else:
                            data = np.zeros_like(data)
                    else:
                        data = np.zeros_like(data)

                    data = np.clip(data * 255, 0, 255).astype("uint8")
                    Image.fromarray(data, mode="RGB").save(temp_preview, "JPEG", quality=85, optimize=True)
                    logger.info("Created rasterio preview: %s", temp_preview)

            except Exception as raster_error:
                logger.warning("Rasterio fallback failed for %s: %s; trying PIL fallback", tif_path, raster_error)
                try:
                    with Image.open(tif_path) as img:
                        if img.mode != 'RGB':
                            img = img.convert('RGB')

                        size = get_optimal_size(tif_path, target_size=target_size)
                        img = img.resize(size, Image.Resampling.LANCZOS)
                        img.save(temp_preview, 'JPEG', quality=85, optimize=True)
                        logger.info("Created PIL preview: %s", temp_preview)

                except Exception as pil_error:
                    logger.error("PIL method also failed for %s: %s", tif_path, pil_error)
                    return None

        # Replace original if successful
        if temp_preview.exists():
            temp_preview.rename(preview_path)
            return str(preview_path)

        return None

    except Exception as e:
        logger.error(f"Failed to create preview for {tif_path}: {e}")
        return None

def create_thumbnail(preview_path: Path, output_dir: Path, size: Tuple[int, int] = (200, 150)) -> Optional[str]:
    """
    Create small thumbnail from preview image

    Args:
        preview_path: Path to preview image
        output_dir: Directory to save thumbnail
        size: Thumbnail dimensions

    Returns:
        Path to thumbnail, or None if failed
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        thumb_name = f"{preview_path.stem}_thumb.jpg"
        thumb_path = output_dir / thumb_name

        with Image.open(preview_path) as img:
            # Create thumbnail maintaining aspect ratio
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumb_path, 'JPEG', quality=75, optimize=True)

        logger.info(f"Created thumbnail: {thumb_path}")
        return str(thumb_path)

    except Exception as e:
        logger.error(f"Failed to create thumbnail: {e}")
        return None

def process_tif_directory(input_dir: Path, output_dir: Path) -> dict:
    """
    Process all TIF files in a directory and create previews

    Args:
        input_dir: Directory containing TIF files
        output_dir: Directory to save preview files

    Returns:
        Dictionary with processing results
    """
    results = {
        'processed': [],
        'failed': [],
        'total': 0
    }

    # Find all TIF files
    tif_files = list(input_dir.glob('**/*.tif')) + list(input_dir.glob('**/*.tiff'))
    results['total'] = len(tif_files)

    logger.info(f"Found {results['total']} TIF files to process")

    for tif_path in tif_files:
        try:
            logger.info(f"Processing: {tif_path}")

            # Create preview
            preview_path = create_web_preview(tif_path, output_dir)

            if preview_path:
                thumb_path = create_thumbnail(Path(preview_path), output_dir / "thumbnails")
                results['processed'].append({
                    'original': str(tif_path),
                    'preview': preview_path,
                    'thumbnail': thumb_path,
                })
                logger.info(f"Successfully processed: {tif_path}")
            else:
                results['failed'].append(str(tif_path))
                logger.error(f"Failed to process: {tif_path}")

        except Exception as e:
            results['failed'].append(str(tif_path))
            logger.error(f"Error processing {tif_path}: {e}")

    logger.info(f"Processing complete. Success: {len(results['processed'])}, Failed: {len(results['failed'])}")
    return results

def optimize_existing_geo_assets(db_session, storage_dir: Path) -> dict:
    """
    Process existing GeoAssets with TIF files and add image_path

    Args:
        db_session: Database session
        storage_dir: Base storage directory

    Returns:
        Dictionary with optimization results
    """
    from app.models.geo_asset import GeoAsset

    results = {
        'processed': [],
        'failed': [],
        'skipped': []
    }

    # Get all TIF GeoAssets
    tif_assets = db_session.query(GeoAsset).filter(
        GeoAsset.file_type.in_(['栅格', '影像']) |
        GeoAsset.sub_type.in_(['影像', '栅格'])
    ).all()

    logger.info(f"Found {len(tif_assets)} TIF assets to optimize")

    for asset in tif_assets:
        try:
            # Get full path
            full_path = storage_dir / asset.file_path

            if not full_path.exists():
                logger.warning(f"File not found: {full_path}")
                results['skipped'].append(asset.id)
                continue

            # Create preview directory
            preview_dir = storage_dir / 'previews' / f'asset_{asset.id}'

            # Create preview
            preview_path = create_web_preview(full_path, preview_dir)

            if preview_path:
                # Update asset with image path
                asset.image_path = preview_path.replace(str(storage_dir) + '/', '')

                # Create thumbnail
                thumb_path = create_thumbnail(
                    Path(preview_path),
                    preview_dir / 'thumbnails'
                )

                if thumb_path:
                    asset.image_path += f",thumb:{thumb_path.replace(str(storage_dir) + '/', '')}"

                results['processed'].append(asset.id)
                logger.info(f"Optimized asset {asset.id}: {asset.name}")
            else:
                results['failed'].append(asset.id)
                logger.error(f"Failed to optimize asset {asset.id}")

        except Exception as e:
            results['failed'].append(asset.id)
            logger.error(f"Error optimizing asset {asset.id}: {e}")

    # Commit changes
    db_session.commit()

    logger.info(f"Optimization complete. Processed: {len(results['processed'])}, Failed: {len(results['failed'])}, Skipped: {len(results['skipped'])}")
    return results


def optimize_asset_preview(tif_path: Path, storage_dir: Path, asset_id: int) -> Optional[str]:
    """
    Generate web preview + thumbnail for a single GeoTIFF asset and return the
    relative image_path value stored in the database.
    """
    preview_dir = storage_dir / "previews" / f"asset_{asset_id}"
    preview_path = create_web_preview(tif_path, preview_dir)
    if not preview_path:
        return None

    relative_preview = Path(preview_path).relative_to(storage_dir).as_posix()
    image_path_value = relative_preview

    thumb_path = create_thumbnail(Path(preview_path), preview_dir / "thumbnails")
    if thumb_path:
        relative_thumb = Path(thumb_path).relative_to(storage_dir).as_posix()
        image_path_value = f"{image_path_value},thumb:{relative_thumb}"

    return image_path_value

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Optimize TIF images for web display")
    parser.add_argument('--input', type=Path, required=True, help="Input directory containing TIF files")
    parser.add_argument('--output', type=Path, required=True, help="Output directory for preview images")
    parser.add_argument('--database', action='store_true', help="Process existing GeoAssets")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.database:
        from app.core.database import get_db
        db = next(get_db())
        results = optimize_existing_geo_assets(db, args.input)
    else:
        results = process_tif_directory(args.input, args.output)

    print("\nProcessing Results:")
    print(f"Total files: {results['total'] if 'total' in results else len(results['processed']) + len(results['failed'])}")
    print(f"Processed: {len(results['processed'])}")
    print(f"Failed: {len(results['failed'])}")
    if 'skipped' in results:
        print(f"Skipped: {len(results['skipped'])}")
