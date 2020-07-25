import pygeoip
import geoip2.database
import geoip2.errors
import os
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


db_loaded = False
db = None
db_v6 = None


def load_db_settings():
    """Loads the db settings. Checks in the django settings for the paths to the GEOIP and
    GEOIPV6 databases. If not found it uses the default databases"""

    # Default database paths
    current_dir = Path(__file__).parent
    GEOIP_DEFAULT_DATABASE = current_dir / 'GeoLiteCity.dat'
    GEOIPV6_DEFAULT_DATABASE = current_dir / 'GeoLiteCityv6.dat'
    GEOIP2_DEFAULT_DATABASE = current_dir / 'GeoLite2-City.mmdb'

    # Loading the settings
    GEOIP_VERSION = getattr(settings, 'GEOIP_VERSION', 1)
    if GEOIP_VERSION not in [1, 2]:
        raise ImproperlyConfigured(
            "GEOIP_VERSION setting is defined, but only versions 1 and 2 "
            "are supported")
    if GEOIP_VERSION == 1:
        GEOIP_DATABASE = getattr(settings, 'GEOIP_DATABASE', GEOIP_DEFAULT_DATABASE)
    elif GEOIP_VERSION == 2:
        GEOIP_DATABASE = getattr(settings, 'GEOIP_DATABASE', GEOIP2_DEFAULT_DATABASE)

    if not GEOIP_DATABASE:
        raise ImproperlyConfigured(
            "GEOIP_DATABASE setting has not been properly defined.")
    if not os.path.exists(GEOIP_DATABASE):
        raise ImproperlyConfigured(
            "GEOIP_DATABASE setting is defined, but {} does not exist.".format(
                GEOIP_DATABASE)
        )

    #
    # Version 2 databases combine both ipv4 and ipv6 data, so only one
    # database file is used for both
    #
    GEOIPV6_DATABASE = getattr(settings, 'GEOIPV6_DATABASE', GEOIPV6_DEFAULT_DATABASE)
    if GEOIP_VERSION == 1:
        if not GEOIPV6_DATABASE:
            raise ImproperlyConfigured(
                "GEOIPV6_DATABASE setting has not been properly defined.")
        if not os.path.exists(GEOIPV6_DATABASE):
            raise ImproperlyConfigured(
                "GEOIPV6_DATABASE setting is defined, but file does not exist.")

    return (GEOIP_DATABASE, GEOIPV6_DATABASE, GEOIP_VERSION)


load_db_settings()


def load_db():
    GEOIP_DATABASE, GEOIPV6_DATABASE, GEOIP_VERSION = load_db_settings()

    global db
    global db_v6
    global db_loaded

    if GEOIP_VERSION == 1:
        db = pygeoip.GeoIP(GEOIP_DATABASE, pygeoip.MEMORY_CACHE)
        db_v6 = pygeoip.GeoIP(GEOIPV6_DATABASE, pygeoip.MEMORY_CACHE)
    elif GEOIP_VERSION == 2:
        db = geoip2.database.Reader(GEOIP_DATABASE)

    db_loaded = True


def lookup_tz_v1(ip):
    """
    Lookup a timezone for the ip using the v1 database.

    :param ip: the ip address, v4 or v6
    :return:   the timezone

    """
    if not db_loaded:
        if ':' in ip:
            return db_v6.time_zone_by_addr(ip)
        else:
            return db.time_zone_by_addr(ip)


def lookup_tz_v2(ip):
    """
    Lookup a timezone for the ip using the v2 database.

    :param ip: the ip address, v4 or v6
    :return:   the timezone

    """
    if not db_loaded:
        load_db()
    #
    # v2 databases support both ipv4 an ipv6
    #
    try:
        response = db.city(ip)
    except geoip2.errors.AddressNotFoundError:
        return None
    return response.location.time_zone


# TODO: deprecate to use of one lookup() function
def lookup_country(ip):
    GEOIP_VERSION = getattr(settings, 'GEOIP_VERSION', 1)
    if GEOIP_VERSION != 2:
        raise ImproperlyConfigured("Must use GOIP_VERSION2 for lookup_country functionality.")

    try:
        response = db.city(ip)
    except geoip2.errors.AddressNotFoundError:
        return 'IN'
    return response.country.iso_code


def lookup_city(ip):
    GEOIP_VERSION = getattr(settings, 'GEOIP_VERSION', 1)
    if GEOIP_VERSION != 2:
        raise ImproperlyConfigured("Must use GOIP_VERSION2 for lookup_city functionality.")

    try:
        response = db.city(ip)
    except geoip2.errors.AddressNotFoundError:
        return 'IN'
    return response.city


def lookup(ip):
    """
    Performs one lookup and returns a dict with the following:
    - City
    - Country
    - Continent
    - Timezone
    - Latitude
    - Longitude
    """
    GEOIP_VERSION = getattr(settings, 'GEOIP_VERSION', 1)
    if GEOIP_VERSION != 2:
        raise ImproperlyConfigured("Must use GOIP_VERSION2 for general lookup functionality.")

    try:
        response = db.city(ip)
    except geoip2.errors.AddressNotFoundError:
        return {
            'city': 'Malavli',
            'country': 'IN',
            'continent': 'Asia',
            'timezone': 'Asia/Kolkata',
            'latitude': '18.746380',
            'longitude': '73.473010',
        }
    return {
            'city': response.city,
            'country': response.country.iso_code,
            'continent': response.city.continent,
            'timezone': response.location.time_zone,
            'latitude': response.location.latitude,
            'longitude': response.location.longitude,
    }
