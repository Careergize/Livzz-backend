"""
URL configuration for smart_pg project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from property.urls import urlpatterns as property_patterns
from property.global_views import LocationsView

# Root CRUD routes belong to their domain apps. Owner workflows remain under
# /seeker/ for compatibility with existing clients.
public_property_patterns = [route for route in property_patterns if str(route.pattern) not in ('', 'tenants/', 'payments/')]

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API v1 endpoints

        path('auth/', include('accounts.urls')),
        path('seeker/', include('property.urls', namespace='seeker')),
        path('', include((public_property_patterns, 'property'), namespace='property')),
        path('locations/', LocationsView.as_view(), name='locations'),
        path('', include('rooms.urls')),
        path('', include('Tenant.urls')),
        path('', include('visitor.urls')),
        path('', include('staff.urls')),
        path('', include('grocery.urls')),
        path('', include('maintenance.urls')),
        path('', include('payments.urls'))

]

# This allows Django to serve the images in the /media/ folder
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
