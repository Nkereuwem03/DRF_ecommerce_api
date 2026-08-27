from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import (
    InvalidToken,
    TokenError,
)
from rest_framework_simplejwt.tokens import RefreshToken

from config.error_handling.response import error_response, success_response

from .serializers import (
    LoginSerializer,
    RegistrationSerializer,
    TokenRefreshRequestSerializer,
    UserDetailSerializer,
    VerifyEmailSerializer,
)
from .services.auth_service import AuthService


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = AuthService.register(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        return success_response(
            message=("Account created successfully. Please verify your email"),
            data={
                "id": str(user.id),
                "email": user.email,
                "email_verified": False,
                "verification_required": True,
            },
            status_code=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = AuthService.verify_email(
            email=serializer.validated_data["email"],
            otp=serializer.validated_data["otp"],
        )

        refresh = RefreshToken.for_user(user)

        return success_response(
            message="Email verified successfully",
            data={
                "id": str(user.id),
                "email": user.email,
                "email_verified": True,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status_code=status.HTTP_200_OK,
        )


class CustomTokenObtainPairView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = AuthService.login(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )
        except ValidationError as e:
            return error_response(
                message=str(e.detail[0])
                if isinstance(e.detail, list)
                else str(e.detail),
                errors={"code": e.get_codes()},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        user = result["user"]

        return success_response(
            message="Login successful",
            data={
                "id": str(user.id),
                "email": user.email,
                "is_email_verified": user.is_email_verified,
                "access": result["access"],
                "refresh": result["refresh"],
            },
            status_code=status.HTTP_200_OK,
        )


class CustomTokenRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = TokenRefreshRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = AuthService.refresh_token(serializer.validated_data["refresh"])
        except InvalidToken as e:
            return error_response(
                message=str(e),
                errors={"code": "token_not_valid"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        return success_response(
            message="Token refreshed successfully",
            data=data,
            status_code=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return error_response(
                message="Refresh token is required",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as e:
            return error_response(
                message=f"Invalid refresh token: {e!s}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            message="Successfully logged out",
            status_code=status.HTTP_205_RESET_CONTENT,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user)

        return success_response(
            message="",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )
