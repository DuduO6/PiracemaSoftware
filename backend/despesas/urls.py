from rest_framework import routers
from django.urls import path, include
from .views import CategoriaDespesaViewSet, DespesaViewSet, FuncionarioDespesaViewSet

router = routers.DefaultRouter()
router.register(r'categorias', CategoriaDespesaViewSet, basename='categoria')
router.register(r'despesas', DespesaViewSet, basename='despesa')
router.register(r'funcionarios', FuncionarioDespesaViewSet, basename='funcionario')

urlpatterns = router.urls
