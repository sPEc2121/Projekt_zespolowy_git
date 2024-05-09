from geopy.geocoders import Nominatim

def get_coordinates(address, city):
    full_address = f"{address}, {city}"
    geolocator = Nominatim(user_agent="my_geocoder")
    location = geolocator.geocode(full_address)
    if location:
        latitude, longitude = location.latitude, location.longitude
        return latitude, longitude
    else:
        return None, None