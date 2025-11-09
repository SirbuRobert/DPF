from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profil/', views.profil_view, name='profil'),
    path('materii/', views.materii_view, name='materii'),
    path('import-elevi/', views.import_elevi_view, name='import_elevi'),
    path('quiz/',views.quiz_view, name='quiz'),
    path("lectii/<int:lectie_id>/ai/", views.lectie_ai_view, name="lectie_ai"),
    path("material/<int:pk>/", views.material_text_view, name="material_text"),
    path("api/summarize-selection/", views.api_summarize_selection, name="api_summarize_selection"),
    path('lectie_ai/<int:lectie_id>/', views.lectie_ai_view, name='lectie_ai'),
    path('quiz/', views.quiz_view, name='quiz'),
    path('import_elevi/', views.import_elevi_view, name='import_elevi'),
    path('profil/', views.profil_view, name='profil'),
    path('profesori/', views.profesori_view, name='profesori'), 
    path('chat/', views.chat_inbox_view, name='chat_inbox'), # <-- ACEASTĂ LINIE NOUĂ TREBUIE SĂ EXISTE
    path('chat/<int:destinatar_id>/', views.chat_view, name='chat'), 
    path('chat/ajax/<int:destinatar_id>/', views.get_messages_ajax_view, name='chat_ajax_messages'), 
]