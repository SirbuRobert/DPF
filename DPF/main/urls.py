from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profil/', views.profil_view, name='profil'),
    path('materii/', views.materii_view, name='materii'),
    path('import-elevi/', views.import_elevi_view, name='import_elevi'),
    path('quiz/',views.quiz_view, name='quiz'),
    path("lectii/<int:lectie_id>/ai/", views.lectie_ai_view, name="lectie_ai"),

]