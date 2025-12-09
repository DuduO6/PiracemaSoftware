from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MotoristaViewSet, ValeViewSet

router = DefaultRouter()
router.register(r'motoristas', MotoristaViewSet, basename="motoristas")
router.register(r'vales', ValeViewSet, basename="vales")

urlpatterns = [
    path('', include(router.urls)),
]
