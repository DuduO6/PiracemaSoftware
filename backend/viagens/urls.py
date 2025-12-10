from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ViagemViewSet

router = DefaultRouter()
router.register(r'', ViagemViewSet, basename='viagem')

urlpatterns = [
    path('', include(router.urls)),
]
