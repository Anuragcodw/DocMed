from appointment.models import Appointment, DoctorProfile
from django.db.models import Q
import math

class DoctorRecommender:
    def recommend_doctors(self, specialty: str = None, user_lat: float = None, user_lng: float = None, limit: int = 5) -> list:
        # Fetch active appointments
        qs = Appointment.objects.select_related('user', 'user__doctor_profile')
        
        if specialty:
            # Match department or qualification
            qs = qs.filter(
                Q(department__icontains=specialty) | 
                Q(qualification_name__icontains=specialty)
            )

        doctors_list = []
        for apt in qs:
            dp = getattr(apt.user, 'doctor_profile', None)
            
            # Calculate distance if coordinates are present
            distance = None
            if user_lat is not None and user_lng is not None and dp and dp.latitude and dp.longitude:
                rad = math.pi / 180
                dlat = (dp.latitude - user_lat) * rad
                dlon = (dp.longitude - user_lng) * rad
                a = (math.sin(dlat / 2) ** 2 +
                     math.cos(user_lat * rad) * math.cos(dp.latitude * rad) *
                     math.sin(dlon / 2) ** 2)
                distance = round(6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 1) # km

            # Calculate composite ranking score
            rating = dp.rating if dp else 4.0
            experience = dp.experience_years if dp else 2
            is_verified = dp.is_verified if dp else False
            fee = getattr(apt, 'appointment_fee', 500) # default standard fee
            if not isinstance(fee, (int, float)):
                fee = 500

            # Scoring: Higher rating, more experience, closer distance, lower fee is better
            score = (rating * 10) + (experience * 0.5)
            if is_verified:
                score += 15
            if distance is not None:
                # Deduct points based on distance (closer = higher score)
                score -= min(distance * 0.2, 20)
            if fee:
                # Deduct points based on high fee
                score -= min(float(fee) * 0.01, 15)

            doctors_list.append({
                'appointment': apt,
                'doctor_profile': dp,
                'distance_km': distance,
                'score': round(score, 2)
            })

        # Sort by composite score descending
        doctors_list.sort(key=lambda x: x['score'], reverse=True)
        return doctors_list[:limit]
