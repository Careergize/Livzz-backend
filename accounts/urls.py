from django.urls import path
from .views import (
    SendOTPView, VerifyOTPView, RegisterSeekerView, RegisterOwnerView,
    LoginView, LogoutView
)

app_name = 'accounts'

urlpatterns = [
    # Authentication & Onboarding
    path('send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('register/seeker/', RegisterSeekerView.as_view(), name='register_seeker'),
    path('register/owner/', RegisterOwnerView.as_view(), name='register_owner'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
