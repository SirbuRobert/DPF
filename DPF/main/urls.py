from django.urls import path
from . import views  # Importăm funcțiile din views.py (din același folder)

urlpatterns = [
    # Când cineva accesează adresa "rădăcină" a acestei aplicații
    # (pe care o vom defini ca 'dashboard/' în pasul următor),
    # rulează funcția numită 'dashboard_view'.
    path('', views.dashboard_view, name='dashboard'),
    
    # --- Aici vei adăuga viitoarele tale URL-uri din 'main' ---
    # De exemplu:
    # path('adauga-material/', views.adauga_material_view, name='adauga_material'),
    # path('profil/', views.profil_view, name='profil'),
]