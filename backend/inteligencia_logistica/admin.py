from django.contrib import admin

from .models import Empresa, MembroEmpresa, PracaPedagio, RouteCache, TarifaPedagio


admin.site.register((Empresa, MembroEmpresa, PracaPedagio, TarifaPedagio, RouteCache))
