from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from main.views import home_view # Importăm view-ul pt homepage

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Pagina principală (/) va fi gestionată de 'home_view'
    path('', home_view, name='home'), 
    
    # Restul URL-urilor (login, register etc.) le delegăm aplicației 'main'
    path('', include('main.urls')),
]

# Adăugăm configurarea pentru fișierele MEDIA (așa cum am făcut înainte)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)