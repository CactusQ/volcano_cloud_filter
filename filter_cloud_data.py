# Custom classes from other files
from get_modvolc_data import get_modvolc_data
from get_modis_images import get_modis_images
from get_volcano_info import get_volcano_info

# Python native
import os
from concurrent.futures import ThreadPoolExecutor
from concurrent import futures
import datetime
import time

# External packages
import matplotlib.pyplot as plt
import requests
import argparse
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from PIL import Image



# Threads used for parallel computation
MAX_THREADS = 50

CLOUD_MEAN_GB_THRESHOLD = 150        # if mean(Band2 + Band1) > this threshold: pixel could be cloud corrupted
SNOW_R_THRESHOLD = 75               # if pixel could be cloud, but Band7 (R) is lower than this value, it is snow or ice
VEGETATION_GB_RATIO_THRESHOLD = 1.5  # if pixel could be cloud, but has a lot higher Band2 (G) than Band1 (B) value, it is vegetation
CLOUD_RATIO_THRESHOLD = 0.2          # If the fraction of Cloud pixels in the image is higher, it is corrupted


"""
    Compute cloud mask for the image in the file_path
    INPUT  - filepath
    OUTPUT - ratio of cloud_pixels / total_pixels
"""

def compute_cloud_mask(file_path):
    cloud_fraction = 0
    if os.path.isfile(file_path):
        image = Image.open(file_path)
        # Dismiss if image is all one color (usually all black for corrupted URLs)
        extrema = image.convert("L").getextrema()
        if extrema[0] == extrema[1]:
            pass

        cloud_pixel_count = 0
        if image.getbbox():
            image_rgb = image.convert("RGB")  
            result = image_rgb
            for x in range(image_rgb.width):
                for y in range(image_rgb.height):

                    # MODIS Bands 7, 2, 1 (R = 2155 nm; G = 876 nm; B = 670 nm)
                    R, G, B = image_rgb.getpixel((x,y))

                    # source: https://earthdata.nasa.gov/faq/worldview-snapshots-faq#modis-721
                    # Possible cloud pixels have both high G and B values, 
                    # whereas snow and ice also have low R values
                    cloud_pixel = ((G+B) / 2  >= CLOUD_MEAN_GB_THRESHOLD        and
                                            R >  SNOW_R_THRESHOLD               and
                                          G/B <  VEGETATION_GB_RATIO_THRESHOLD)
                    if not cloud_pixel:
                        result.putpixel((x,y), (0,0,0)) # Cut out non-cloud pixels from cloud_mask
                    else:
                        cloud_pixel_count += 1

            # Save cloud mask
            result.save(f"{file_path[:-4]}_cloud_mask.png")
            cloud_fraction = cloud_pixel_count / (image_rgb.width*image_rgb.height)

    return cloud_fraction


""" 
    Saves MODVOLC data with information about cloud corruption as .csv
"""
def main(name, year, number_of_days, day_in_year, g, remove_files):

    vdf = get_volcano_info(name)
    vdf = vdf.iloc[0]

    print("=================================")
    print("Found the following volcano data:")
    print(vdf)
    print("=================================")

    aperture = vdf['aperture'] if g is None else g
    volcano_name = vdf['volcano_name']
    DATA_DIR = f"data/{volcano_name}/"
    DATA_DIR_MODIS_IMAGES = f"data/{volcano_name}/modis_images/"

    # Compute bounding box
    lonmin = round(vdf['lon'] - aperture/2, 4)
    lonmax = round(vdf['lon'] + aperture/2, 4)
    latmin = round(vdf['lat'] - aperture/2, 4)
    latmax = round(vdf['lat'] + aperture/2, 4)

    # Get MODVOLC data for volcano and the aperture as bounding box
    df = get_modvolc_data(year, day_in_year, number_of_days, lonmin, lonmax, latmin, latmax)

    if df is pd.DataFrame.empty:
        print("No hot spot alerts found for given period and volcano.")  
        exit()

    # Dates of interests = Dates where hotspots where active
    dates_and_sat = df[['date', 'Sat']]
    dates_and_sat_unique = dates_and_sat.drop_duplicates(subset=['date'])

    aperture_bbox = [latmin, lonmin, latmax, lonmax]

    # Download and save MODIS images for area surrounding volcano
    start_time_download = time.time()
    get_modis_images(volcano_name,
                    aperture_bbox,
                    dates_and_sat_unique['date'],
                    all_layers = dates_and_sat_unique['Sat'],
                    autoscale = False,
                    upscale_resolution = True)
    end_time_download = time.time()


    # Compute the fraction of the image that has been corrupted by clouds
    cloud_fractions = []
    jobs = []
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        
        # Compute mask for each unique date and save results
        for full_date, layers in list(zip(dates_and_sat_unique['date'], dates_and_sat_unique['Sat'])):
            date = str(full_date).split()[0]
            file_path = DATA_DIR_MODIS_IMAGES + f"{date}_{volcano_name}_{layers}.png"
            jobs.append(executor.submit(compute_cloud_mask, file_path))
    
    index = 0
    for job in jobs:
        this_date = df.date.iloc[index]
        cloud_fraction = job.result()

        # One date may have multiple alerts 
        # -> mark all alerts from that date as cloud corrupted
        alerts_count_this_date = df[df.date == this_date].iloc[0]['daily_count']
        for _ in range (alerts_count_this_date):
            cloud_fractions.append(cloud_fraction)

        index += alerts_count_this_date


    df['cloud_fraction'] = np.array(cloud_fractions)
    df['corrupted'] = df['cloud_fraction'] > CLOUD_RATIO_THRESHOLD

    end_date = datetime.date(year, 1, 1) + datetime.timedelta(days=day_in_year)
    start_date = end_date - datetime.timedelta(days=number_of_days)
    period_suffix = f"_from_{start_date}_to_{end_date}"

    # Save MODVOLC data locally
    df.to_csv(f"{DATA_DIR}{volcano_name}_{period_suffix}.csv")

    # Plot spatial points lon vs. lat
    fig, ax = plt.subplots(1, 2, figsize=(27,9), gridspec_kw={'width_ratios': [1, 2]})
    scatter = ax[0].scatter(df.Longitude, df.Latitude, c=df.datetime, s=5)
    cbar = fig.colorbar(scatter, ax=ax[0], orientation='horizontal')
    cbar.set_label('UNIX Time')

    ax[0].set_title("Spatial Measurements")
    ax[0].set_xlabel("Longitude")
    ax[0].set_ylabel("Latitude")

    # Plot number of hotspot alerts vs. date + corrupted days in red, otherwise green
    corrupted_true = df.apply(lambda x: x['daily_count'] if x['corrupted'] else float('nan') , axis=1)
    corrupted_false = df.apply(lambda x: x['daily_count'] if not x['corrupted'] else float('nan') , axis=1)
    scatter = ax[1].plot(df.date, df.daily_count, markersize=3)
    scatter = ax[1].scatter(df.date, corrupted_true, s=40, color='red')
    scatter = ax[1].scatter(df.date, corrupted_false, s=40, color='green')
    ax[1].set_title("Time Series")
    ax[1].set_xlabel("Date")
    plt.xticks(rotation=20)
    ax[1].set_ylabel("Counts")

    fig.suptitle(f"{volcano_name} {period_suffix}")
    plt.savefig(f"{DATA_DIR}/{volcano_name}_spatial_temporal{period_suffix}.png", bbox_inches='tight', dpi=300)

    print("Total amount of hotspots processed: ", len(dates_and_sat_unique['date']))
    print("Time for download: ", str(end_time_download - start_time_download))
    print("Time for cloud_mask processing: ", str(time.time() - end_time_download))

    if remove_files:
        from shutil import rmtree 
        rmtree(DATA_DIR_MODIS_IMAGES)

    return df



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
    For a given volcano and time period, this script saves MODVOLC data and adds a column that indicates corruption by clouds.
    The period is calculated by specificing a specific date (year + offset in days),
    and analyzing the previous N days.
    """)

    parser.add_argument('name', metavar='name', type=str,
                        help='volcano name. should be present in one of the files in /volcano_info]')

    parser.add_argument('year', type=int, default=1,
                        help='year of interest')

    parser.add_argument('N', type=int, default=1,
                        help='length of period in days')

    parser.add_argument('-g', dest='g', type=float, default=None,
                        help='g spans the area of interests around the volcano center -> g X g size (lon/lat) [default = volcano_aperture]')

    parser.add_argument('-d', dest='day_in_year', type=int, default=1,
                        help='offset in days [default = 1]')

    parser.add_argument('-r', action='store_true',
                        help='remove MODIS images and cloud_masks after filtering is done')

    args = parser.parse_args()
    main(args.name, args.year, args.N, args.day_in_year, args.g, args.r)