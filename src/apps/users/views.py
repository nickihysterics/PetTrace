from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.middleware.csrf import get_token
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, response, status, viewsets
from rest_framework.views import APIView

from apps.common.services import get_setting_int, is_feature_enabled

from .models import User, UserAccessProfile, UserMFAProfile
from .serializers import (
    GroupSerializer,
    MFASetupResponseSerializer,
    MFAVerifySerializer,
    SessionLoginResponseSerializer,
    SessionLoginSerializer,
    UserAccessProfileSerializer,
    UserMFAProfileSerializer,
    UserSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related("groups").select_related("access_profile", "mfa_profile").all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ["is_active", "is_staff", "groups"]
    search_fields = ["email", "first_name", "last_name", "phone"]
    ordering_fields = ["created_at", "email"]


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.prefetch_related("permissions").all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAdminUser]
    search_fields = ["name"]


class UserAccessProfileViewSet(viewsets.ModelViewSet):
    queryset = UserAccessProfile.objects.select_related("user", "home_branch").prefetch_related(
        "allowed_branches",
        "allowed_cabinets",
    )
    serializer_class = UserAccessProfileSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ["user", "home_branch", "limit_to_assigned_cabinets"]
    search_fields = ["user__email", "notes"]


class UserMFAProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserMFAProfile.objects.select_related("user").all()
    serializer_class = UserMFAProfileSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ["user", "is_enabled"]
    search_fields = ["user__email"]


def _rate_limit_key(request, email: str) -> str:
    ip = request.META.get("REMOTE_ADDR", "unknown")
    return f"auth:login:{ip}:{email.lower()}"


class SessionLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=SessionLoginSerializer,
        responses={
            200: SessionLoginResponseSerializer,
            401: OpenApiResponse(description="Неверные учетные данные или OTP-код."),
            403: OpenApiResponse(description="Учетная запись пользователя неактивна."),
            429: OpenApiResponse(description="Слишком много попыток входа."),
        },
    )
    def post(self, request):
        serializer = SessionLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        rate_limit_attempts = get_setting_int("auth.rate_limit_attempts", default=10)
        rate_limit_window = get_setting_int("auth.rate_limit_window_seconds", default=300)
        cache_key = _rate_limit_key(request, email)

        attempt_count = int(cache.get(cache_key, 0))
        if attempt_count >= rate_limit_attempts:
            return response.Response(
                {"detail": "Too many login attempts. Please try later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        user = authenticate(
            request,
            email=email,
            password=serializer.validated_data["password"],
        )
        if user is None:
            cache.set(cache_key, attempt_count + 1, timeout=rate_limit_window)
            return response.Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            cache.set(cache_key, attempt_count + 1, timeout=rate_limit_window)
            return response.Response({"detail": "User is inactive."}, status=status.HTTP_403_FORBIDDEN)

        mfa_profile = UserMFAProfile.objects.filter(user=user, is_enabled=True).first()
        if mfa_profile and is_feature_enabled("security.mfa", default=False):
            otp_code = serializer.validated_data.get("otp_code", "")
            if not otp_code:
                cache.set(cache_key, attempt_count + 1, timeout=rate_limit_window)
                return response.Response(
                    {"detail": "MFA code is required.", "mfa_required": True},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            import pyotp

            totp = pyotp.TOTP(mfa_profile.secret_key)
            if not totp.verify(otp_code, valid_window=1):
                cache.set(cache_key, attempt_count + 1, timeout=rate_limit_window)
                return response.Response(
                    {"detail": "Invalid MFA code.", "mfa_required": True},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        cache.delete(cache_key)
        login(request, user)
        return response.Response(
            {
                "user": UserSerializer(user).data,
                "csrf_token": get_token(request),
                "mfa_required": bool(mfa_profile and is_feature_enabled("security.mfa", default=False)),
            },
            status=status.HTTP_200_OK,
        )


class SessionLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=None,
        responses={204: OpenApiResponse(description="Сессия завершена.")},
    )
    def post(self, request):
        logout(request)
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class SessionMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: UserSerializer},
    )
    def get(self, request):
        return response.Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class MFASetupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: MFASetupResponseSerializer},
    )
    def post(self, request):
        import pyotp

        if not is_feature_enabled("security.mfa", default=False):
            return response.Response({"detail": "MFA feature is disabled"}, status=status.HTTP_400_BAD_REQUEST)

        profile, _ = UserMFAProfile.objects.get_or_create(user=request.user)
        if not profile.secret_key:
            profile.secret_key = pyotp.random_base32()
            profile.save(update_fields=["secret_key", "updated_at"])

        app_label = "PetTrace"
        otpauth_uri = pyotp.TOTP(profile.secret_key).provisioning_uri(
            name=request.user.email,
            issuer_name=app_label,
        )
        return response.Response(
            {
                "secret_key": profile.secret_key,
                "otpauth_uri": otpauth_uri,
            }
        )


class MFAVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=MFAVerifySerializer,
        responses={200: UserMFAProfileSerializer},
    )
    def post(self, request):
        import pyotp

        if not is_feature_enabled("security.mfa", default=False):
            return response.Response({"detail": "MFA feature is disabled"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile, _ = UserMFAProfile.objects.get_or_create(user=request.user)
        if not profile.secret_key:
            return response.Response({"detail": "MFA is not initialized"}, status=status.HTTP_400_BAD_REQUEST)

        totp = pyotp.TOTP(profile.secret_key)
        if not totp.verify(serializer.validated_data["otp_code"], valid_window=1):
            return response.Response({"detail": "Invalid MFA code"}, status=status.HTTP_400_BAD_REQUEST)

        profile.is_enabled = True
        profile.save(update_fields=["is_enabled", "updated_at"])
        return response.Response(UserMFAProfileSerializer(profile).data, status=status.HTTP_200_OK)


class MFADisableView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=MFAVerifySerializer,
        responses={200: UserMFAProfileSerializer},
    )
    def post(self, request):
        import pyotp

        serializer = MFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = UserMFAProfile.objects.filter(user=request.user).first()
        if profile is None or not profile.secret_key:
            return response.Response({"detail": "MFA is not initialized"}, status=status.HTTP_400_BAD_REQUEST)

        totp = pyotp.TOTP(profile.secret_key)
        if not totp.verify(serializer.validated_data["otp_code"], valid_window=1):
            return response.Response({"detail": "Invalid MFA code"}, status=status.HTTP_400_BAD_REQUEST)

        profile.is_enabled = False
        profile.save(update_fields=["is_enabled", "updated_at"])
        return response.Response(UserMFAProfileSerializer(profile).data, status=status.HTTP_200_OK)
