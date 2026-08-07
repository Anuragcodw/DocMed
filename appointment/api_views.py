import math
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from .models import DoctorProfile

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees)
    """
    if None in (lat1, lon1, lat2, lon2):
        return float('inf')
        
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers
    return c * r

from .search_service import SearchService

class DoctorsNearbyAPIView(View):
    """
    API endpoint to fetch available doctors, sorted by distance if lat/lon provided.
    Includes OSRM driving distance and estimated travel time.
    """
    def get(self, request, *args, **kwargs):
        lat_str = request.GET.get('lat')
        lon_str = request.GET.get('lon')
        limit = int(request.GET.get('limit', 5))

        user_lat = None
        user_lon = None

        if lat_str and lon_str:
            try:
                user_lat = float(lat_str)
                user_lon = float(lon_str)
            except ValueError:
                pass

        # Get doctors who are verified
        doctors = list(DoctorProfile.objects.filter(is_verified=True).select_related('user'))

        # Filter for availability
        available_doctors = [doc for doc in doctors if doc.is_available_now]
        if not available_doctors:
            available_doctors = doctors[:10]  # Fallback to verified doctors if none online right now

        results = []
        for doc in available_doctors:
            dist_km = None
            duration_min = None
            if user_lat is not None and user_lon is not None and doc.latitude and doc.longitude:
                dist_km, duration_min = SearchService.get_travel_distance_osrm(
                    user_lat, user_lon, doc.latitude, doc.longitude
                )

            photo_url = doc.photo.url if doc.photo else '/static/images/default-doctor.jpg'

            results.append({
                'id': doc.id,
                'first_name': doc.user.first_name,
                'last_name': doc.user.last_name,
                'full_name': doc.full_name,
                'specialization': doc.specialization,
                'hospital': doc.hospital,
                'experience': doc.experience_years,
                'fee': float(doc.consultation_fee),
                'rating': doc.rating,
                'reviews': doc.review_count,
                'photo_url': photo_url,
                'distance_km': dist_km,
                'duration_min': duration_min,
                'latitude': doc.latitude,
                'longitude': doc.longitude,
            })

        if user_lat is not None and user_lon is not None:
            results.sort(key=lambda x: (x['distance_km'] if x['distance_km'] is not None else 9999, -x['rating']))
        else:
            results.sort(key=lambda x: (-x['rating'], -x['reviews']))

        return JsonResponse({'doctors': results[:limit]})
