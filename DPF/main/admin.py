from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, ElevProfile, ProfesorProfile, Materie, MaterialDidactic

# --- 1. Definirea "Inlines" pentru Profile ---
# (Această parte rămâne la fel)

class ElevProfileInline(admin.StackedInline):
    model = ElevProfile
    can_delete = False
    verbose_name_plural = 'Profil Elev'
    extra = 0 

class ProfesorProfileInline(admin.StackedInline):
    model = ProfesorProfile
    can_delete = False
    verbose_name_plural = 'Profil Profesor'
    extra = 0

# --- 2. Configurarea Admin-ului Custom pentru User ---
# (Această parte rămâne la fel)

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informații Personale', {'fields': ('first_name', 'last_name', 'email', 'numar_telefon')}),
        ('Rolul Utilizatorului', {'fields': ('rol',)}), 
        ('Permisiuni', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Date Importante', {'fields': ('last_login', 'date_joined')}),
    )
    
    list_display = ('username', 'first_name', 'last_name', 'rol', 'is_staff')
    list_filter = ('rol', 'is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'numar_telefon')
    
    # Funcția care asigură logica
    def get_inlines(self, request, obj=None):
        if not obj:
            return []
        
        if obj.rol == User.Rol.ELEV:
            return (ElevProfileInline,)
        elif obj.rol == User.Rol.PROFESOR:
            return (ProfesorProfileInline,)
        
        return []

# --- 3. Înregistrarea modelelor Profile (Separat) ---
# 
# ❗ MODIFICARE AICI ❗
# Am comentat/șters înregistrările separate.
# Acest lucru PREVINE eroarea pe care ai găsit-o.
# Profilele vor fi create DOAR din pagina de User.
#
# @admin.register(ElevProfile)
# class ElevProfileAdmin(admin.ModelAdmin):
#     ... (codul vechi a fost șters)
#
# @admin.register(ProfesorProfile)
# class ProfesorProfileAdmin(admin.ModelAdmin):
#     ... (codul vechi a fost șters)


# --- 4. Înregistrarea Materie și MaterialDidactic ---
# (Această parte rămâne, avem nevoie de ea)

@admin.register(Materie)
class MaterieAdmin(admin.ModelAdmin):
    list_display = ('nume',)
    search_fields = ('nume',)

@admin.register(MaterialDidactic)
class MaterialDidacticAdmin(admin.ModelAdmin):
    list_display = ('titlu', 'materie', 'an_studiu', 'autor', 'data_adaugarii')
    list_filter = ('an_studiu', 'materie', 'autor')
    search_fields = ('titlu', 'descriere', 'autor__username', 'materie__nume')
    autocomplete_fields = ['autor', 'materie']
    ordering = ('-data_adaugarii',)