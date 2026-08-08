from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import RegisterView, ProfileView

urlpatterns = [
    # Registration — open endpoint
    path('register/', RegisterView.as_view(), name='auth-register'),

    # JWT token endpoints
    path('login/', TokenObtainPairView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),

    # Authenticated profile — no pk in URL (IDOR-safe)
    path('me/', ProfileView.as_view(), name='auth-me'),
]
