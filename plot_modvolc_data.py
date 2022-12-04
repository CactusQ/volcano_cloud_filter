import pandas as pd
import matplotlib.pyplot as plt

from os import mkdir
from os.path import isdir
from get_modvolc_data import get_modvolc_data

import sys
import requests
import datetime

from bs4 import BeautifulSoup
import argparse

parser = argparse.ArgumentParser(description="""
For a given volcano and time period, this script saves and plots the MODVOLC data.
The period is calculated by specificing a specific date (year + offset in days),
and analyzing the previous N days.
""")

parser.add_argument('name', metavar='name', type=str,
                    help='the name of the volcano [see /data/target_volcanoes.txt]')

parser.add_argument('year', type=int, default=1,
                    help='year of interest')

parser.add_argument('N', type=int, default=1,
                    help='length of period in days')

parser.add_argument('--g', dest='g', type=int, default=0.1,
                    help='g spans the area of interests around the volcano center -> g X g size (lon/lat) [default = 0.1]')

parser.add_argument('--d', dest='day_in_year', type=int, default=1,
                    help='offset in days [default = 1]')

args = parser.parse_args()

name = args.name
year = args.year
day_in_year = args.day_in_year
n = args.N 
day_in_year = args.day_in_year
g = args.g


# Find POST Value for given volcano
target_volcanoes_df = pd.read_csv("volcano_info/target_volcanoes.txt", delimiter='\s', header=None, engine='python')
target_volcanoes_df.columns = ["name"]
post_value_df = target_volcanoes_df[target_volcanoes_df.name == name]

if post_value_df.empty:
    print ("Could not find volcano_name = \'"+name+"\' in the /data/target_volcanoes.txt file. Please check spelling.")
    exit()

# Create data directory 
data_dir = f"data/{name}/"
if not isdir(data_dir):
    mkdir(data_dir)

# Create and send POST request to get URL with MODVOLC data of interest


post_url = 'http://modis.higp.hawaii.edu/cgi-bin/modisnew.cgi'
post_object = {
    'maptype': 'relief',
    'csize': .1,
    'format': 'region',
    'target': post_value_df.index[0],
    'jperiod': str(n),
    'jyear': str(year),
    'jday': str(day_in_year),
}

# The coordinates are written in the title

result_html = requests.post(post_url, data = post_object)
soup = BeautifulSoup(result_html.text, 'html.parser')
title = soup.b.text
title_elements = title.split()
lon = float(title_elements[1])
lat = float(title_elements[3])
# Get corresponding URL

lonmin = lon - g
lonmax = lon + g
latmin = lat - g
latmax = lat + g

# Get MODVOLC data from URL
df = get_modvolc_data(year, day_in_year, n, lonmin, lonmax, latmin, latmax)
print(df)
# Create period suffix for file names
end_date = datetime.date(year, 1, 1) + datetime.timedelta(days=day_in_year)
start_date = end_date - datetime.timedelta(days=n)
period_suffix = f"_from_{start_date}_to_{end_date}"

# Save MODVOLC data locally
df.to_csv(f"{data_dir}{name}{period_suffix}.csv")


# Plot
fig, ax = plt.subplots(1, 2, figsize=(16,9))

scatter = ax[0].scatter(df.Longitude, df.Latitude, c=df.datetime, s=2)
cbar = fig.colorbar(scatter, ax=ax[0], orientation='horizontal')
cbar.set_label('UNIX Time')

#ax[0].add_artist(plt.Circle(target[1:3], target[3]/2., color=]'k', fill=False))
ax[0].set_title("Spatial Measurements")
ax[0].set_xlabel("Longitude")
ax[0].set_ylabel("Latitude")

scatter = ax[1].plot_date(df.datetime, df.B21, markersize=2)

ax[1].set_title("Time Series")
ax[1].set_xlabel("Date")
plt.xticks(rotation=20)
ax[1].set_ylabel("B21")

fig.suptitle(f"{name} [lon={lon}/lat={lat}/{g}x{g}] {period_suffix}")
plt.savefig(f"{data_dir}/{name}_spatial_temporal{period_suffix}.png", bbox_inches='tight', dpi=300)
