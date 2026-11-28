import html
import math
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

st.set_page_config(page_title="Kenya Nearby Services", layout="wide")
st.title("Hospitals and Petrol Stations in Kenya")
st.caption("Searches OpenStreetMap data. An internet connection is required.")

def distance_km(lat1, lon1, lat2, lon2):
    """Calculate the distance between two coordinates using the haversine formula."""
    earth_radius_km = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    )
    return 2 * earth_radius_km * math.asin(math.sqrt(a))

with st.sidebar:
    st.header("Search area")
    latitude = st.number_input(
        "Latitude", min_value=-4.8, max_value=5.2, value=-1.2864, format="%.6f"
    )
    longitude = st.number_input(
        "Longitude", min_value=33.8, max_value=42.0, value=36.8172, format="%.6f"
    )
    radius_km = st.slider("Search radius (km)", 1, 50, 10)
    search = st.button("Find nearby places", type="primary")

if search:
    radius_m = radius_km * 1000
    query = f"""
    [out:json][timeout:25];
    (
      node(around:{radius_m},{latitude},{longitude})["amenity"~"^(hospital|fuel)$"];
      way(around:{radius_m},{latitude},{longitude})["amenity"~"^(hospital|fuel)$"];
      relation(around:{radius_m},{latitude},{longitude})["amenity"~"^(hospital|fuel)$"];
    );
    out center tags;
    """

    try:
        with st.spinner("Searching OpenStreetMap…"):
            response = requests.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=40,
                headers={"User-Agent": "KenyaNearbyServices/1.0"},
            )
            response.raise_for_status()
            elements = response.json().get("elements", [])

        places = []
        for item in elements:
            tags = item.get("tags", {})
            lat = item.get("lat", item.get("center", {}).get("lat"))
            lon = item.get("lon", item.get("center", {}).get("lon"))
            if lat is None or lon is None:
                continue

            kind = tags.get("amenity")
            places.append(
                {
                    "name": tags.get("name", "Unnamed place"),
                    "type": "Hospital" if kind == "hospital" else "Petrol station",
                    "lat": lat,
                    "lon": lon,
                    "distance": distance_km(latitude, longitude, lat, lon),
                    "address": ", ".join(
                        value
                        for value in [
                            tags.get("addr:street"),
                            tags.get("addr:city"),
                        ]
                        if value
                    ),
                }
            )

        places.sort(key=lambda place: place["distance"])

        if not places:
            st.info("No hospitals or petrol stations found in that search area.")
        else:
            map_view = folium.Map(
                location=[latitude, longitude],
                zoom_start=12,
                control_scale=True,
            )
            folium.Marker(
                [latitude, longitude],
                tooltip="Search location",
                popup="Your search location",
                icon=folium.Icon(color="blue", icon="user"),
            ).add_to(map_view)

            for place in places:
                color = "red" if place["type"] == "Hospital" else "green"
                popup = (
                    f"<b>{html.escape(place['name'])}</b><br>"
                    f"{html.escape(place['type'])}<br>"
                    f"{place['distance']:.1f} km away"
                )
                if place["address"]:
                    popup += f"<br>{html.escape(place['address'])}"

                folium.Marker(
                    [place["lat"], place["lon"]],
                    tooltip=f"{place['type']}: {place['name']}",
                    popup=folium.Popup(popup, max_width=250),
                    icon=folium.Icon(color=color, icon="plus-sign"),
                ).add_to(map_view)

            st_folium(map_view, use_container_width=True, height=550)

            st.subheader(f"Results ({len(places)})")
            for place in places:
                address = f" — {place['address']}" if place["address"] else ""
                st.write(
                    f"**{place['type']}**: {place['name']} "
                    f"({place['distance']:.1f} km){address}"
                )

    except requests.RequestException as error:
        st.error(f"Could not retrieve map data. Please try again later. ({error})")
    except ValueError:
        st.error("The map service returned data that could not be read.")
else:
    st.write(
        "Enter a location's latitude and longitude in the sidebar, "
        "choose a search radius, and click **Find nearby places**."
    )
