"""
URL configuration for common app (health checks).
"""
from django.urls import path
from apps.common import views

app_name = 'common'

urlpatterns = [
    path('', views.health_check, name='health_check'),
    path('db/', views.health_db, name='health_db'),
    path('cache/', views.health_cache, name='health_cache'),
]

