# TIF Image Optimization Workflow Guide

This guide explains how to optimize TIF image display in the vue-map application.

## Overview

The TIF optimization workflow includes:
1. Database migration to add `image_path` field
2. GDAL utility for generating optimized web previews
3. Frontend components with skeleton loading and full-screen preview

## Prerequisites

### Backend Dependencies
Install required packages:
```bash
pip install -r requirements-optimization.txt
```

Required packages:
- Pillow>=9.0.0
- rasterio>=1.3.0
- GDAL>=3.4.0

### GDAL Installation

On macOS with Homebrew:
```bash
brew install gdal
```

On Ubuntu/Debian:
```bash
sudo apt-get install gdal-bin libgdal-dev
```

## Setup Instructions

### 1. Database Migration

Run the migration script to add the `image_path` field:

```bash
cd /Users/mengzh/Desktop/vue-map/backend
python add_image_path_field.py
```

This will:
- Add `image_path` column to `geo_assets` table
- Create an index for better performance

### 2. Update Model Schema

The `GeoAsset` model and API schema already include the `image_path` field.

### 3. Process Existing TIF Files

To optimize existing TIF files, run:

```bash
# For all TIF files in storage directory
python utils/optimize_tif.py --input /path/to/storage --output /path/to/storage/previews --database
```

This will:
- Create optimized JPEG previews (800x600 max)
- Generate thumbnails (200x150)
- Update database with image paths
- Handle both new and existing files

## Frontend Implementation

The frontend has been updated with:

### InfoPanel.vue Features

1. **Skeleton Loading State**
   - Shows while image is loading
   - Smooth animations for better UX

2. **Full-Screen Preview**
   - Click thumbnail to view full size
   - Supports zoom and pan
   - Download option

3. **Error Handling**
   - Graceful fallback for missing images
   - User-friendly error messages

## API Changes

### New Endpoints

1. **Download with Preview Option**
   ```
   GET /api/geodata/download/{asset_id}?preview=true
   ```

2. **Response Includes Image Path**
   ```json
   {
     "id": 1,
     "name": "geological_map",
     "file_path": "maps/geological.tif",
     "image_path": "previews/asset_1/geological_map_preview.jpg,thumb:previews/asset_1/thumbnails/geological_map_thumb.jpg",
     "type": "栅格",
     "sub_type": "影像"
   }
   ```

## Configuration

### Storage Structure

```
storage/
├── original_tifs/          # Original TIF files
├── previews/               # Optimized previews
│   ├── asset_1/            # Per-asset directory
│   │   ├── geological_map_preview.jpg
│   │   └── thumbnails/
│   │       └── geological_map_thumb.jpg
│   └── asset_2/
│       └── ...
└── ...
```

### Performance Considerations

1. **Preview Size**: 800x600 provides good balance between quality and load time
2. **Thumbnail Size**: 200x150 for quick loading in lists
3. **Compression**: JPEG with 85% quality for web display
4. **Lazy Loading**: Images load only when visible

## Troubleshooting

### Common Issues

1. **GDAL not found**
   - Ensure GDAL is installed and in PATH
   - Check `gdalinfo` command works

2. **Image optimization fails**
   - Check file permissions
   - Verify TIF file is not corrupted
   - Ensure enough disk space

3. **Images not displaying**
   - Check `image_path` is populated in database
   - Verify file paths are correct
   - Check web server serves files from storage directory

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Testing

1. Upload new TIF file through web interface
2. Verify preview appears in InfoPanel
3. Test full-screen preview and download
4. Check existing files after running optimization script

## Future Enhancements

1. **WebP Support**: Use WebP format for better compression
2. **Multi-band Support**: Handle multi-band TIF files
3. **Progressive Loading**: Load low-res first, then high-res
4. **Cache Control**: Add cache headers for better performance

## Migration Notes

- Existing TIF files will not have optimized previews until processed
- The migration script is safe to run multiple times
- Original files are never modified
- Backups are recommended before processing large datasets