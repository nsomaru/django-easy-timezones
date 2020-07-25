import django
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from .signals import detected_timezone
from .utils import get_ip_address_from_request, is_valid_ip, is_local_ip
from . import load_db, db_loaded, lookup_tz_v1, lookup_tz_v2, lookup_country, lookup_city


if django.VERSION >= (1, 10):
    from django.utils.deprecation import MiddlewareMixin
    middleware_base_class = MiddlewareMixin
else:
    middleware_base_class = object


class EasyTimezoneMiddleware(middleware_base_class):
    def process_request(self, request):
        """
        If we can get a valid IP from the request,
        look up that address in the database to get the appropriate timezone
        and activate it.

        Else, use the default.

        """

        if not request:
            return

        if not db_loaded:
            load_db()

        tz = request.session.get('django_timezone')

        version = getattr(settings, 'GEOIP_VERSION')

        if not tz:
            # use the default timezone (settings.TIME_ZONE) for localhost
            tz = timezone.get_default_timezone()

            client_ip = get_ip_address_from_request(request)
            ip_addrs = client_ip.split(',')
            for ip in ip_addrs:
                if is_valid_ip(ip) and not is_local_ip(ip):
                    if version == 1:
                        tz = lookup_tz_v1(ip)
                    else:
                        tz = lookup_tz_v2(ip)

        if tz:
            timezone.activate(tz)
            request.session['django_timezone'] = str(tz)
            if getattr(settings, 'AUTH_USER_MODEL', None) and getattr(request, 'user', None):
                detected_timezone.send(sender=get_user_model(), instance=request.user, timezone=tz)
        else:
            timezone.deactivate()

        country = request.session.get('django_country')
        if not country:
            country = 'IN'  # default
            client_ip = get_ip_address_from_request(request)
            ip_addrs = client_ip.split(',')
            for ip in ip_addrs:
                if is_valid_ip(ip) and not is_local_ip(ip):
                    if version == 2:
                        country = lookup_country(ip)
                        break

        if country:
            request.session['django_country'] = country

        city = request.session.get('django_city')
        if not city:
            city = 'Mumbai'  # default
            client_ip = get_ip_address_from_request(request)
            ip_addrs = client_ip.split(',')
            for ip in ip_addrs:
                if is_valid_ip(ip) and not is_local_ip(ip):
                    if version == 2:
                        city = lookup_city(ip)
                        break

        if city:
            request.session['django_city'] = city
