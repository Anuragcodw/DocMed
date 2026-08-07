import math
import logging
from django.db.models import Q
from accounts.models import User
from .models import Appointment, DoctorProfile, DEPARTMENT_CHOICES

logger = logging.getLogger(__name__)

class SearchService:
    """
    Encapsulates advanced search, filtering, nearby calculation, 
    and search suggestions logic for the DocMed Healthcare Platform.
    """

    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Calculate Haversine distance in kilometers between two GPS coordinates."""
        if None in (lat1, lon1, lat2, lon2):
            return None
        
        rad = math.pi / 180.0
        dlat = (lat2 - lat1) * rad
        dlon = (lon2 - lon1) * rad
        
        a = (math.sin(dlat / 2.0) ** 2 +
             math.cos(lat1 * rad) * math.cos(lat2 * rad) *
             math.sin(dlon / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return 6371.0 * c # Earth radius is ~6371 km

    @staticmethod
    def get_travel_distance_osrm(lat1, lon1, lat2, lon2):
        """
        Calculates driving route distance (km) and estimated duration (mins)
        between two coordinates using the free OSRM (Open Source Routing Machine) API.
        Falls back to Haversine distance if OSRM service is offline.
        """
        if None in (lat1, lon1, lat2, lon2):
            return None, None
        try:
            import requests as req
            url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
            res = req.get(url, timeout=3)
            if res.status_code == 200:
                data = res.json()
                if data.get('routes'):
                    route = data['routes'][0]
                    dist_km = round(route['distance'] / 1000.0, 1)
                    duration_min = math.ceil(route['duration'] / 60.0)
                    return dist_km, duration_min
        except Exception:
            pass

        # Fallback to straight-line Haversine distance
        haversine_dist = SearchService.calculate_distance(lat1, lon1, lat2, lon2)
        if haversine_dist is not None:
            # Estimate driving time assuming ~30 km/h average city speed
            est_duration = math.ceil((haversine_dist / 30.0) * 60)
            return round(haversine_dist, 1), est_duration

        return None, None

    @classmethod
    def get_nearby_doctor_ids(cls, ref_lat, ref_lng, max_dist_km=50):
        """Returns doctor user_ids within max_dist_km of reference coordinates."""
        if ref_lat is None or ref_lng is None:
            return []
        
        nearby_ids = []
        # Filter profiles having coordinates
        profiles = DoctorProfile.objects.filter(latitude__isnull=False, longitude__isnull=False)
        
        for profile in profiles:
            dist = cls.calculate_distance(ref_lat, ref_lng, profile.latitude, profile.longitude)
            if dist is not None and dist <= max_dist_km:
                nearby_ids.append(profile.user_id)
        
        return nearby_ids

    @classmethod
    def filter_appointments(cls, request, query_params):
        """
        Applies advanced filters on Appointment slots based on query parameters.
        Returns a tuple of: (filtered_queryset, fallback_level)
        """
        location = query_params.get('location', '').strip()
        department = query_params.get('department', '').strip()
        doctor_name = query_params.get('doctor_name', '').strip()
        gender = query_params.get('gender', '').strip()
        experience = query_params.get('experience', '').strip()
        
        # New advanced filters
        min_fee = query_params.get('min_fee')
        max_fee = query_params.get('max_fee')
        min_rating = query_params.get('min_rating')
        only_verified = query_params.get('only_verified') == 'true'
        only_available = query_params.get('only_available') == 'true'
        insurance_accepted = query_params.get('insurance_accepted') == 'true'
        language = query_params.get('language', '').strip()
        
        # User coordinates for distance filtering
        user_lat = query_params.get('latitude')
        user_lng = query_params.get('longitude')
        max_dist = query_params.get('distance') # km

        qs = Appointment.objects.select_related('user', 'user__doctor_profile').order_by('-created_at')

        # ── Apply Filters ──────────────────────────────────────────────────────
        if department:
            qs = qs.filter(department__icontains=department)

        if doctor_name:
            qs = qs.filter(
                Q(full_name__icontains=doctor_name) |
                Q(user__first_name__icontains=doctor_name) |
                Q(user__last_name__icontains=doctor_name)
            )

        if gender:
            qs = qs.filter(user__gender=gender)

        if experience:
            if experience == '1-5':
                qs = qs.filter(user__doctor_profile__experience_years__range=(1, 5))
            elif experience == '5-10':
                qs = qs.filter(user__doctor_profile__experience_years__range=(5, 10))
            elif experience == '10+':
                qs = qs.filter(user__doctor_profile__experience_years__gte=10)

        if min_fee:
            qs = qs.filter(user__doctor_profile__consultation_fee__gte=float(min_fee))
        if max_fee:
            qs = qs.filter(user__doctor_profile__consultation_fee__lte=float(max_fee))
        if min_rating:
            qs = qs.filter(user__doctor_profile__rating__gte=float(min_rating))
        if only_verified:
            qs = qs.filter(user__doctor_profile__is_verified=True)
        if only_available:
            qs = qs.filter(user__doctor_profile__is_available_today=True)
        if language:
            qs = qs.filter(user__doctor_profile__languages__icontains=language)

        # In a real system, checking insurance accepted would query a linked model.
        # Since it's a fallback, we check if patient insurance field has references.
        # If checked, filter doctors who work at clinics accepting policies (dummy flag or hospital name query).
        if insurance_accepted:
            qs = qs.filter(user__doctor_profile__is_verified=True) # Proxy verification

        # GPS Geolocation filter
        if user_lat and user_lng and max_dist:
            try:
                ref_lat = float(user_lat)
                ref_lng = float(user_lng)
                ref_dist = float(max_dist)
                doc_ids = cls.get_nearby_doctor_ids(ref_lat, ref_lng, ref_dist)
                qs = qs.filter(user_id__in=doc_ids)
            except ValueError:
                pass

        # Location text fallback routing
        fallback_level = None
        if location and not (user_lat and user_lng and max_dist):
            # Check exact match first
            loc_qs = qs.filter(location__icontains=location)
            if loc_qs.exists():
                return loc_qs, None

            # Same City fallback
            same_city_qs = qs.filter(user__doctor_profile__city__iexact=location)
            if same_city_qs.exists():
                return same_city_qs, None

            # Nearby City (Haversine 100km)
            ref_lat, ref_lng = None, None
            ref_doc = DoctorProfile.objects.filter(city__iexact=location).first()
            if ref_doc and ref_doc.latitude and ref_doc.longitude:
                ref_lat, ref_lng = ref_doc.latitude, ref_doc.longitude
            elif request.user.is_authenticated:
                pat = getattr(request.user, 'patient_profile', None)
                if pat and pat.latitude and pat.longitude:
                    ref_lat, ref_lng = pat.latitude, pat.longitude

            if ref_lat is not None:
                doc_ids = cls.get_nearby_doctor_ids(ref_lat, ref_lng, 100)
                nearby_qs = qs.filter(user_id__in=doc_ids)
                if nearby_qs.exists():
                    return nearby_qs, 'nearby'

            # Same State fallback
            state_qs = qs.filter(user__doctor_profile__state__iexact=location)
            if state_qs.exists():
                return state_qs, 'state'

            # Any available doctor
            avail_ids = [doc.user_id for doc in DoctorProfile.objects.filter(is_available_today=True)]
            avail_qs = qs.filter(user_id__in=avail_ids)
            if avail_qs.exists():
                return avail_qs, 'any'

            fallback_level = 'any'

        return qs, fallback_level

    @staticmethod
    def get_search_suggestions(query_text):
        """Returns autocomplete items matching query_text (doctors, departments, locations)."""
        suggestions = []
        if not query_text:
            return suggestions

        q = query_text.strip().lower()

        # Suggest Departments
        for code, label in DEPARTMENT_CHOICES:
            if q in label.lower():
                suggestions.append({
                    'type': 'department',
                    'label': f"{label} (Department)",
                    'value': label,
                    'code': code
                })

        # Suggest Doctors
        docs = DoctorProfile.objects.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(specialization__icontains=q)
        ).select_related('user')[:5]

        for doc in docs:
            suggestions.append({
                'type': 'doctor',
                'label': f"Dr. {doc.full_name} ({doc.specialization})",
                'value': doc.full_name,
                'pk': doc.user.pk
            })

        # Suggest Cities / Locations
        cities = DoctorProfile.objects.filter(city__icontains=q).values_list('city', flat=True).distinct()[:3]
        for city in cities:
            if city:
                suggestions.append({
                    'type': 'location',
                    'label': f"{city} (City)",
                    'value': city
                })

        return suggestions
