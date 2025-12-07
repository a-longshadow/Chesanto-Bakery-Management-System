from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls')),  # Authentication, home, and profile URLs
    
    # ✅ FOUNDATION APPS
    path('inventory/', include('apps.inventory.urls')),  # ✅ Inventory Management
    path('products/', include('apps.products.urls')),    # ✅ Product Catalog & Recipes
    path('production/', include('apps.production.urls')),  # ✅ Production Batches & Stock
    path('sales/', include('apps.sales.urls')),          # ✅ Sales Dispatches & Returns
    path('payroll/', include('apps.payroll.urls')),      # ✅ Payroll & Employee Management
    
    # 📊 REPORTS & ANALYTICS
    path('reports/', include('apps.reports.urls')),      # 📊 Reports (ACCOUNTANT+ access)
    path('analytics/', include('apps.analytics.urls')),  # 📊 Analytics (ACCOUNTANT+ access)
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)