from osgeo import gdal
import numpy as np
import os

# Define output path
output_dir = "/Users/mengzh/Desktop/vue-map/backend/app/storage/rasters/"
os.makedirs(output_dir, exist_ok=True)
output_filepath = os.path.join(output_dir, "test_geotiff.tif")

# Define image properties
width = 100
height = 100
num_bands = 1
pixel_size = 0.1
origin_x = 116.0
origin_y = 40.0

# Create a new GeoTIFF file
driver = gdal.GetDriverByName("GTiff")
dataset = driver.Create(output_filepath, width, height, num_bands, gdal.GDT_Byte)

# Set geotransform (top-left x, pixel width, rotation, top-left y, rotation, pixel height)
geotransform = (origin_x, pixel_size, 0, origin_y, 0, -pixel_size)
dataset.SetGeoTransform(geotransform)

# Set projection (WGS84)
srs = gdal.osr.SpatialReference()
srs.SetWellKnownGeogCS("WGS84")
dataset.SetProjection(srs.ExportToWkt())

# Write some dummy data to the band
band = dataset.GetRasterBand(1)
data = np.random.randint(0, 256, size=(height, width), dtype=np.uint8)
band.WriteArray(data)

# Close the dataset
dataset = None

print(f"Generated dummy GeoTIFF at: {output_filepath}")
