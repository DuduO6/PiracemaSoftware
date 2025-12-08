from rest_framework import generics
from .serializers import RegisterSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer


class LoginView(generics.GenericAPIView):
    def post(self, request):
        username_or_email = request.data.get("user")
        password = request.data.get("password")

        # tenta login por username
        user = authenticate(username=username_or_email, password=password)

        # tenta login por email
        if user is None:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                u = User.objects.get(email=username_or_email)
                user = authenticate(username=u.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is None:
            return Response({"error": "Credenciais inválidas"}, status=400)

        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "username": user.username,
            "email": user.email
        })
