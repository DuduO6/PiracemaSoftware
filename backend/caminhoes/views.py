from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Caminhao
from .serializers import CaminhaoSerializer

class CaminhaoViewSet(viewsets.ModelViewSet):
    serializer_class = CaminhaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Caminhao.objects.filter(usuario=self.request.user)
