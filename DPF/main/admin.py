from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, ElevProfile, ProfesorProfile, Materie, MaterialDidactic

# --- 1. Definirea "Inlines" pentru Profile ---

class ElevProfileInline(admin.StackedInline):
    """Permite editarea profilului de Elev în interiorul paginii User."""
    model = ElevProfile
    can_delete = False
    verbose_name_plural = 'Profil Elev'
    extra = 0 

class ProfesorProfileInline(admin.StackedInline):
    """Permite editarea profilului de Profesor în interiorul paginii User."""
    model = ProfesorProfile
    can_delete = False
    verbose_name_plural = 'Profil Profesor'
    extra = 0

# --- 2. Configurarea Admin-ului Custom pentru User ---

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    """
    Configurare avansată pentru modelul User în admin.
    """
    
    # Adăugăm câmpurile noastre custom în formularul de editare
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informații Personale', {'fields': ('first_name', 'last_name', 'email', 'numar_telefon')}),
        ('Rolul Utilizatorului', {'fields': ('rol',)}), 
        ('Permisiuni', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Date Importante', {'fields': ('last_login', 'date_joined')}),
    )
    
    # Adăugăm câmpurile custom în lista principală (coloanele)
    list_display = ('username', 'first_name', 'last_name', 'rol', 'is_staff')
    
    # Adăugăm 'rol' ca filtru în dreapta
    list_filter = ('rol', 'is_staff', 'is_superuser', 'is_active', 'groups')
    
    # Adăugăm câmpurile noastre la căutare
    search_fields = ('username', 'first_name', 'last_name', 'email', 'numar_telefon')
    
    # Funcție pentru a afișa profilul corect (Elev sau Profesor)
    def get_inlines(self, request, obj=None):
        if not obj:
            return []
        
        if obj.rol == User.Rol.ELEV:
            return (ElevProfileInline,)
        elif obj.rol == User.Rol.PROFESOR:
            return (ProfesorProfileInline,)
        
        return []

# --- 3. Înregistrarea modelelor Profile (Separat) ---

@admin.register(ElevProfile)
class ElevProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_nume_complet', 'an_studiu', 'clasa_litera')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    list_filter = ('an_studiu', 'clasa_litera')
    
    @admin.display(description='Nume Complet', ordering='user__first_name')
    def get_nume_complet(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

@admin.register(ProfesorProfile)
class ProfesorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_nume_complet', 'materie_predata')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    list_filter = ('materie_predata',)
    autocomplete_fields = ['materie_predata'] # Facilitează alegerea materiei
    
    @admin.display(description='Nume Complet', ordering='user__first_name')
    def get_nume_complet(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

# --- 4. Înregistrarea noilor modele (Materie și MaterialDidactic) ---

@admin.register(Materie)
class MaterieAdmin(admin.ModelAdmin):
    """Configurare admin pentru Materii."""
    list_display = ('nume',)
    search_fields = ('nume',) # Necesar pentru autocomplete_fields în ProfesorProfile

@admin.register(MaterialDidactic)
class MaterialDidacticAdmin(admin.ModelAdmin):
    """Configurare admin pentru Materiale Didactice."""
    list_display = ('titlu', 'materie', 'an_studiu', 'autor', 'data_adaugarii')
    list_filter = ('an_studiu', 'materie', 'autor')
    search_fields = ('titlu', 'descriere', 'autor__username', 'materie__nume')
    
    # Folosim autocomplete pentru a selecta ușor autorul și materia
    # (foarte util când ai sute de useri sau materii)
    autocomplete_fields = ['autor', 'materie']
    
    # Ordonare implicită
    ordering = ('-data_adaugarii',)