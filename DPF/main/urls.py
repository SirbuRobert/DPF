from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profil/', views.profil_view, name='profil'),
    path('materii/', views.materii_view, name='materii'),
    path('import-elevi/', views.import_elevi_view, name='import_elevi'),
]