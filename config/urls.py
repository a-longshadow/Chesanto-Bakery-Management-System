from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls')),  # Authentication, home, and profile URLs
    path('products/', include('apps.products.urls')),  # Products app URLs
    path('inventory/', include('apps.inventory.urls')),  # Inventory app URLs
    path('production/', include('apps.production.urls')),  # Production app URLs
    path('sales/', include('apps.sales.urls')),  # Sales app URLs
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)