# --- În main/views.py ---
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import MaterialDidactic, User

@login_required # Blochează accesul dacă nu e logat
def dashboard_view(request):
    
    # Luăm userul logat
    user = request.user
    context = {} # Datele pe care le trimitem la HTML

    if user.rol == User.Rol.ELEV:
        # --- LOGICĂ PENTRU ELEV ---
        an_elev = user.elev_profile.an_studiu
        
        # Luăm materialele doar pentru anul lui
        materiale = MaterialDidactic.objects.filter(an_studiu=an_elev)
        
        context['materiale'] = materiale
        template_name = 'main/dashboard_elev.html' # Îi trimitem un HTML de elev

    elif user.rol == User.Rol.PROFESOR:
        # --- LOGICĂ PENTRU PROFESOR ---
        
        # Luăm materialele create de el SAU care sunt de la materia lui
        # (alegem o logică, de ex. cele create de el)
        materiale = MaterialDidactic.objects.filter(autor=user)
        
        context['materiale'] = materiale
        template_name = 'main/dashboard_profesor.html' # Îi trimitem un HTML de profesor

    else:
        # (Dacă e admin sau altceva, un dashboard generic)
        template_name = 'main/dashboard_admin.html'

    
    return render(request, template_name, context)