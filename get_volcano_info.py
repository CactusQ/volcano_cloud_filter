import argparse
from bs4 import BeautifulSoup
import requests
import pandas as pd


DEFAULT_APERTURE = float(0.2)        # Default aperture assumption

"""
    Fetch data about the target volcano
    INPUT:
        name - volcano name (insensitive to case and special character )

    OUTPUT:
        1-row   pd.DataFrame([name, lon, lat, aperture])
"""

def get_volcano_info(name):

    # removed special chars and upper / lower case
    target_volcano_df = pd.DataFrame.empty
    aperture_df = pd.read_csv("volcano_info/apertures.csv", delimiter=',', header=None, engine='python')
    aperture_df.columns = ['volcano_name','lon','lat','aperture']
    target_volcano_df = aperture_df[aperture_df.volcano_name == name]
    if target_volcano_df.empty:
        print ("Could not find target_volcano = \'"+name+"\' in the /volcano_info/apertures.csv file.")
        print ("Trying to find volcano in /volcano_info/available_volcanoes.txt file and fetch location.")

        available_volcanoes_df = pd.read_csv("volcano_info/available_volcanoes.txt", delimiter='\s', header=None, engine='python')
        available_volcanoes_df.columns = ["volcano_name"]
        target_volcano_df = available_volcanoes_df[available_volcanoes_df.volcano_name == name]

        if target_volcano_df.empty:
            print ("Could not find volcano_name = \'"+name+"\' in the /volcano_info/available_volcanoes.txt file.")
            print ("Please check manually if your volcano is in the files or add it.")
            exit()
        
        # Create and send POST request to get URL with MODVOLC data of interest
        post_url = 'http://modis.higp.hawaii.edu/cgi-bin/modisnew.cgi'
        post_object = {
            'maptype': 'relief',
            'csize': .1,
            'format': 'region',
            'target': target_volcano_df.index[0],
            'jperiod': "1", 
            'jyear': "2020",
            'jday': "1",
        }

        # The coordinates are written in the title
        result_html = requests.post(post_url, data = post_object)
        soup = BeautifulSoup(result_html.text, 'html.parser')
        title = soup.b.text
        title_elements = title.split()
        target_volcano_df =  pd.DataFrame({
                "volcano_name": [name],
                "lon": [float(title_elements[1])],
                "lat": [float(title_elements[3])],
                "aperture": [DEFAULT_APERTURE]})

    target_volcano_df.volcano_name = target_volcano_df.volcano_name.str.replace('\W', '').str.lower()


    return target_volcano_df