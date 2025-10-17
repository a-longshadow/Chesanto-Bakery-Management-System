from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

# Home route redirects to login (no public home page)
def home_redirect(request):
    """Redirect all users to login page (no public access)"""
    if request.user.is_authenticated:
        # Redirect based on role
        if request.user.role == 'BASIC_USER':
            return redirect('user_profile', user_id=request.user.id)
        else:
            return redirect('profile')
    return redirect('login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls')),  # Authentication and profile URLs
    path('', home_redirect, name='home'),  # Redirect to login (no public home)
    path('health/', lambda request: redirect('login'), name='health'),  # Health check also requires auth
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)