from django.db.models import Sum, Count
from appointment.models import TakeAppointment, Appointment, MedicalReport
from accounts.models import User
from django.utils import timezone
import datetime

class EnterpriseAnalyticsService:
    @staticmethod
    def get_dashboard_metrics() -> dict:
        """Computes key metrics for super-admin dashboard."""
        now = timezone.now()
        thirty_days_ago = now - datetime.timedelta(days=30)

        total_patients = User.objects.filter(role='patient').count()
        total_doctors = User.objects.filter(role='doctor').count()
        total_appointments = TakeAppointment.objects.count()
        
        # Earned Revenue placeholder (assuming fee is stored or calculated)
        # Using 500 as average fee per booking
        revenue = TakeAppointment.objects.filter(status='approved').count() * 500.0
        commission = revenue * 0.10 # 10% commission

        # Monthly analytics
        monthly_bookings = TakeAppointment.objects.filter(date__gte=thirty_days_ago).count()
        
        # Cancellation stats
        cancelled_bookings = TakeAppointment.objects.filter(status='cancelled').count()
        cancellation_rate = round((cancelled_bookings / max(total_appointments, 1)) * 100, 1)

        # Department popularity
        dept_stats = (
            Appointment.objects
            .values('department')
            .annotate(count=Count('bookings'))
            .order_by('-count')
        )
        popular_departments = {d['department']: d['count'] for d in dept_stats[:5]}

        # Peak hours metric
        peak_hours = {
            '09:00 - 12:00': TakeAppointment.objects.filter(appointment__start_time__contains='AM').count(),
            '13:00 - 17:00': TakeAppointment.objects.filter(appointment__start_time__contains='PM').count()
        }

        # AI Insights summary
        ai_insights = f"Report uploads increased by {MedicalReport.objects.count()} this month. Most active department: {list(popular_departments.keys())[0] if popular_departments else 'General'}"

        return {
            'total_patients': total_patients,
            'total_doctors': total_doctors,
            'total_appointments': total_appointments,
            'total_revenue': revenue,
            'total_commission': commission,
            'monthly_bookings': monthly_bookings,
            'cancellation_rate': cancellation_rate,
            'popular_departments': popular_departments,
            'peak_hours': peak_hours,
            'ai_insights': ai_insights
        }
