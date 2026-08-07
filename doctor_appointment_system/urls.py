"""
Root URL configuration for doctor_appointment_system.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('accounts.urls')),
    path('', include('appointment.urls')),

    # OpenAPI 3 Schema & Interactive API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers
handler400 = 'django.views.defaults.bad_request'
handler403 = 'django.views.defaults.permission_denied'
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'

