# DPF/main/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, ElevProfile, ProfesorProfile, 
    Materie, Lectie, MaterialDidactic
)

# --- 1. Admin pentru User și Profile ---

class ElevProfileInline(admin.StackedInline):
    """Permite editarea profilului de elev direct din pagina de user."""
    model = ElevProfile
    can_delete = False
    verbose_name_plural = 'Profil Elev'

class ProfesorProfileInline(admin.StackedInline):
    """Permite editarea profilului de profesor direct din pagina de user."""
    model = ProfesorProfile
    can_delete = False
    verbose_name_plural = 'Profil Profesor'

class CustomUserAdmin(UserAdmin):
    """Extindem adminul de User pentru a include profilele."""
    inlines = (ElevProfileInline, ProfesorProfileInline)
    
    # Adăugăm 'rol' în lista de câmpuri afișate
    list_display = ('username', 'first_name', 'last_name', 'rol', 'is_staff')
    
    # Adăugăm 'rol' la filtre
    list_filter = UserAdmin.list_filter + ('rol',)
    
    # Adăugăm 'rol' la câmpurile editabile în admin
    fieldsets = UserAdmin.fieldsets + (
        ('Informații Suplimentare', {'fields': ('rol', 'numar_telefon')}),
    )

# --- MODIFICAREA CARE REZOLVĂ EROAREA ---
# Verificăm dacă modelul User (al nostru) este deja înregistrat de Django
# (ceea ce ar trebui să facă automat aplicația 'auth')
if admin.site.is_registered(User):
    # Doar dacă este înregistrat, îl dezregistrăm
    admin.site.unregister(User)

# Acum îl înregistrăm noi, cu setările noastre customizate
admin.site.register(User, CustomUserAdmin)


# --- 2. Admin pentru Materii, Lecții și Materiale (NOUA STRUCTURĂ) ---

class MaterialDidacticInline(admin.StackedInline):
    """
    Permite adăugarea de Materiale (PDF-uri)
    direct din pagina de creare/editare a unei Lecții.
    """
    model = MaterialDidactic
    extra = 1 # Afișează 1 formular gol pentru materiale noi
    verbose_name = "Material Didactic"
    verbose_name_plural = "Materiale Didactice"

@admin.register(Lectie)
class LectieAdmin(admin.ModelAdmin):
    """Admin pentru modelul Lecție."""
    list_display = ('titlu', 'materie', 'get_an_studiu_display')
    list_filter = ('an_studiu', 'materie')
    search_fields = ('titlu', 'materie__nume')
    
    inlines = [MaterialDidacticInline] # Adaugă materiale direct în lecție

    class Meta:
       model = Lectie

class LectieInline(admin.StackedInline):
    """
    Permite adăugarea de Lecții
    direct din pagina de creare/editare a unei Materii.
    """
    model = Lectie
    extra = 1 # Afișează 1 formular gol pentru lecții noi
    verbose_name = "Lecție"
    verbose_name_plural = "Lecții"


@admin.register(Materie)
class MaterieAdmin(admin.ModelAdmin):
    """Admin pentru modelul Materie."""
    list_display = ('nume',)
    search_fields = ('nume',)
    
    inlines = [LectieInline] # Adaugă lecții direct în materie

@admin.register(MaterialDidactic)
class MaterialDidacticAdmin(admin.ModelAdmin):
    """Admin pentru Materiale (listă generală)."""
    list_display = ('titlu', 'lectie', 'autor', 'fisier')
    list_filter = ('lectie__materie', 'lectie__an_studiu', 'autor')
    search_fields = ('titlu', 'lectie__titlu')