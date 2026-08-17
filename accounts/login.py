from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
# from rest_framework_simplejwt.tokens import RefreshToken

class LoginView(APIView):

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)

        if user is not None:
            # refresh = RefreshToken.for_user(user)

            return Response({
                "message": "Login successful",
                # "access": str(refresh.access_token),
                # "refresh": str(refresh),
                "role": user.role,
                "username": user.username
            })

        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)