from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    MeView,
    SendOTPView,
    VerifyOTPView,
    AccountRegistrationView,
    EmailVerifyView,
    ResendVerificationView,
    CustomLoginView,
    ForgotPasswordView,
    SetForgotPasswordView,
    UpdatePasswordView,
    LogoutAPIView
)

urlpatterns = [
    path("register/", AccountRegistrationView.as_view(), name="register"),
    path("verify-email/", EmailVerifyView.as_view(), name="verify-email"),
    path("resend-verify/", ResendVerificationView.as_view(), name="resend-verify"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path(
        "set-password/<uidb64>/<token>/",
        SetForgotPasswordView.as_view(),
        name="set_forgot_password",
    ),
    path("update-password/", UpdatePasswordView.as_view(), name="change_password"),
    path("/logout", LogoutAPIView.as_view(), name="logout"),
    # path("otp/send/", SendOTPView.as_view(), name="otp-send"),
    # path("otp/verify/", VerifyOTPView.as_view(), name="otp-verify"),
    # path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    # path("me/", MeView.as_view(), name="me"),
    # path("/token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    # path("/social/google", GoogleLoginView.as_view(), name="google-login"),


    # path("/profile", UserProfileView.as_view(), name="user-profile"),
    # path(
    #     "/accept-invite/<uuid:alias>",
    #     AcceptInviteView.as_view(),
    #     name="accept-invite",
    # ),
]
