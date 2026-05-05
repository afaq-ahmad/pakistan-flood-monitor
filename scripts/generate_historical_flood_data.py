import json
import time
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# Past 20 years of major floods and worst-hit districts in Pakistan
FLOOD_DATA = [
    {
        "year": 2005,
        "name": "2005 Winter Floods / Snowmelt",
        "districts": ["Peshawar", "Nowshera", "Charsadda", "Swat", "Dir", "Chitral", "Quetta", "Turbat"]
    },
    {
        "year": 2007,
        "name": "2007 Cyclone Yemyin Floods",
        "districts": ["Kech", "Turbat", "Gwadar", "Awaran", "Lasbela", "Jhal Magsi", "Dadu"]
    },
    {
        "year": 2010,
        "name": "2010 Mega Floods",
        "districts": ["Nowshera", "Charsadda", "Swat", "Shangla", "Muzaffargarh", "Rajanpur", "Dera Ghazi Khan", "Jacobabad", "Shikarpur", "Kashmore", "Dadu", "Thatta", "Sujawal"]
    },
    {
        "year": 2011,
        "name": "2011 Sindh Floods",
        "districts": ["Badin", "Mirpur Khas", "Tharparkar", "Umerkot", "Tando Allahyar", "Tando Muhammad Khan", "Shaheed Benazirabad"]
    },
    {
        "year": 2012,
        "name": "2012 Monsoon Floods",
        "districts": ["Jacobabad", "Kashmore", "Shikarpur", "Rajanpur", "Dera Ghazi Khan"]
    },
    {
        "year": 2014,
        "name": "2014 Punjab Floods",
        "districts": ["Hafizabad", "Gujranwala", "Sialkot", "Mandi Bahauddin", "Jhang", "Multan", "Muzaffargarh", "Chiniot"]
    },
    {
        "year": 2020,
        "name": "2020 Urban & Monsoon Floods",
        "districts": ["Karachi", "Hyderabad", "Dadu", "Badin", "Sujawal"]
    },
    {
        "year": 2022,
        "name": "2022 Mega Floods",
        "districts": ["Dadu", "Jamshoro", "Khairpur", "Naushahro Feroze", "Sanghar", "Shaheed Benazirabad", "Shikarpur", "Sukkur", "Kambar Shahdadkot", "Larkana", "Rajanpur", "Dera Ghazi Khan", "Nowshera", "Charsadda", "Swat"]
    }
]

def geocode_districts():
    geolocator = Nominatim(user_agent="pakistan-flood-monitor-historical")
    district_coords = {}
    
    # Collect unique districts
    unique_districts = set()
    for event in FLOOD_DATA:
        unique_districts.update(event["districts"])
        
    print(f"Geocoding {len(unique_districts)} unique districts in Pakistan...")
    
    for district in sorted(unique_districts):
        query = f"{district} District, Pakistan"
        retries = 3
        while retries > 0:
            try:
                location = geolocator.geocode(query, geometry='geojson')
                if not location:
                    # Try without "District"
                    location = geolocator.geocode(f"{district}, Pakistan", geometry='geojson')
                
                if location:
                    district_coords[district] = {
                        "lat": location.latitude,
                        "lon": location.longitude,
                        "raw_bbox": location.raw.get("boundingbox") # [lat_min, lat_max, lon_min, lon_max]
                    }
                    print(f"  [+] Found {district}: {location.latitude}, {location.longitude}")
                else:
                    print(f"  [-] Not found: {district}")
                break
            except (GeocoderTimedOut, GeocoderUnavailable):
                retries -= 1
                time.sleep(2)
        time.sleep(1) # respect API limits
        
    # Build final dataset
    final_dataset = []
    for event in FLOOD_DATA:
        event_regions = []
        for dist in event["districts"]:
            if dist in district_coords:
                event_regions.append({
                    "name": dist,
                    "lat": district_coords[dist]["lat"],
                    "lon": district_coords[dist]["lon"],
                    "boundingbox": district_coords[dist]["raw_bbox"]
                })
            else:
                print(f"Warning: Missing coordinates for {dist} in {event['year']}")
        
        final_dataset.append({
            "year": event["year"],
            "name": event["name"],
            "regions": event_regions
        })
        
    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "historical_flood_regions.json"
    
    with open(out_file, "w") as f:
        json.dump(final_dataset, f, indent=2)
        
    print(f"Saved dataset to {out_file} with {len(final_dataset)} historical events.")

if __name__ == "__main__":
    geocode_districts()
