# OS
import os
import argparse
import requests
import datetime
from concurrent.futures import ThreadPoolExecutor
from concurrent import futures

# Threads used for parallel image download
MAX_THREADS = 50


# Same scaling NASA uses on their snapshot website
LAT_TO_KM = 113.7775

# For full list see: https://earthdata.nasa.gov/faq/worldview-snapshots-faq#base-layers
AVAILABLE_LAYERS = [
    "MODIS_Terra_CorrectedReflectance_Bands721",
    "MODIS_Terra_CorrectedReflectance_Bands367",
    "MODIS_Terra_CorrectedReflectance_TrueColor",
    "MODIS_Aqua_CorrectedReflectance_Bands721",
    "MODIS_Aqua_CorrectedReflectance_Bands367",
    "MODIS_Aqua_CorrectedReflectance_TrueColor"
]

"""
    Download and save content of image_url to saving_path
"""

def download_image(image_url, saving_path):
    if os.path.isfile(saving_path):
        print(f'{saving_path} already exists. Skipping')
        return
    r = requests.get(image_url, stream=True)
    if r.status_code == 200:
        r.raw.decode_content = True    
        with open(saving_path, 'wb') as handler:
            handler.write(r.content)
            print(f'Saved {saving_path}.')
    else:
        print(f'{image_url} could not be downloaded.')


"""
    Fetch and locally save MODIS Image data
    INPUT:
        volcano_name        - target_volcano from /volcano_info/target_volcanoes.txt
        bounding_box        - [latmin, lonmin, latmax, lonmax]
        all_dates           - List of dates to download as Datetime or Strings in "YYYY-MM-DD"
        all_layers          - List of satellite layers from AVAILABLE_LAYERS
        autoscale           - let server resize image width to get a pseudo-equal-area image
        upscale_resolution  - increase resolution by using 250m x 250m per pixel images

    output:
        None
"""

def get_modis_images(volcano_name,
                    bounding_box,
                    all_dates,
                    all_layers = "MODIS_Terra_CorrectedReflectance_Bands721",
                    autoscale = True,
                    upscale_resolution = True):

    SCALE_RESOLTION = 4 if upscale_resolution else 1
    AUTOSCALE = "TRUE" if autoscale else "FALSE"
    latmin, lonmin, latmax, lonmax = bounding_box
    BBOX=f"{latmin},{lonmin},{latmax},{lonmax}"

    # Create data directory for plots and MODIS images
    data_dir = f"data/{volcano_name}/"
    data_dir_modis_images = f"data/{volcano_name}/modis_images/"
    if not os.path.isdir(data_dir):
        os.mkdir(data_dir)
    if not os.path.isdir(data_dir_modis_images):
        os.mkdir(data_dir_modis_images)

    # One pixel should equal 1000m and the image should be square
    # This is overridden if autoscale == True
    delta_lat_km = (latmax - latmin) * LAT_TO_KM
    HEIGHT = int(delta_lat_km) * SCALE_RESOLTION
    WIDTH = HEIGHT

    # Multi threaded download and saving
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        base_url = "https://wvs.earthdata.nasa.gov/api/v1/snapshot?REQUEST=GetSnapshot"

        for date, layer in list(zip(all_dates, all_layers)):
            if layer == 'T':
                layer_id = "MODIS_Terra_CorrectedReflectance_Bands721"
            else:
                layer_id = "MODIS_Aqua_CorrectedReflectance_Bands721"
            date = str(date).split(" ")[0]
            filename = f"{date}_{volcano_name}_{layer}.png"
            saving_path = data_dir_modis_images + filename

            image_url = base_url + f"&LAYERS={layer_id}&CRS=EPSG:4326&TIME={date}"
            image_url += f"&WRAP=DAY&BBOX={BBOX}&FORMAT=image/png&WORLDFILE=false"
            image_url += f"&WIDTH={WIDTH}&HEIGHT={HEIGHT}&AUTOSCALE={AUTOSCALE}"

            executor.submit(download_image, image_url, saving_path)