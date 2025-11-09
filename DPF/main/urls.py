from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('materii/', views.materii_view, name='materii'),
    path('lectie_ai/<int:lectie_id>/', views.lectie_ai_view, name='lectie_ai'),
    path('quiz/', views.quiz_view, name='quiz'),
    path('import_elevi/', views.import_elevi_view, name='import_elevi'),
    path('profil/', views.profil_view, name='profil'),
    path('profesori/', views.profesori_view, name='profesori'), 
    path('chat/<int:destinatar_id>/', views.chat_view, name='chat'),
    path('chat/ajax/<int:destinatar_id>/', views.get_messages_ajax_view, name='chat_ajax_messages'), 
]