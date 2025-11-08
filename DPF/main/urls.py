from django.urls import path
from . import views

urlpatterns = [
    # Am șters path-ul '' de aici (e acum în urls.py principal)
    
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profil/', views.profil_view, name='profil'),
    path('materii/', views.materii_view, name='materii'),
    # Poți adăuga 'quiz', 'chat' aici pe viitor
]