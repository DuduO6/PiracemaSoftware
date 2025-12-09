from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Caminhao
from .serializers import CaminhaoSerializer

class CaminhaoViewSet(viewsets.ModelViewSet):
    queryset = Caminhao.objects.all()
    serializer_class = CaminhaoSerializer
    permission_classes = [IsAuthenticated]
