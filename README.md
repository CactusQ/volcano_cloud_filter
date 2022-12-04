
# Spectroscopic Cloud Filtering on Satellite Images of Volcanic Hotspots

  

This Python package provides tools to download historical data and satellite images of volcano hot spots and filter clouds through spectral analysis. <br>

Hot spots are identified through the [**MODVOLC** API](http://modis.higp.hawaii.edu/). Their respective satellite images are downloaded via **[NASA's WorldView API (MODIS)](https://wvs.earthdata.nasa.gov/)**. <br>

One central challenge in analyzing thermal imagery of volcanoes is the abundance of periods with major cloud coverage. We propose a simple approach (thermal spectral analysis) to determine cloud coverage in (and subsequently filter from) low-resolution satellite imagery by analyzing the RGB composition of pixels (please refer to the ***report.pdf*** for further elaboration). 

Satellite images are downloaded and filtered in folders separated by volcano (**/data**). The historical data of hots pot occurrences will also be saved (**CSV**) and plotted for further processing (eruption prediction, trend analysis, ...). 

  

# Usage

Run the main script to check input arguments and their description:

  

```

python3 filter_cloud_data.py

```

  

Example to download hotspot satellite images and plot hotspot history for **Etna** during the last **100 days**:

  

```

python3 filter_cloud_data.py Etna 100

```


You can find all available volcanoes in the **/volcano_info** folder, and add new volcano names by appending them to **available_volcanoes.txt**. The script will try to find the volcano aperture in **apertures.csv**, otherwise it will assume a default aperture. If desired, you can also parametrize the thresholds for the cloud filtering process and other variables by changing the constants in the scripts.
