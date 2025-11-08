# DPF/main/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms # <-- IMPORTĂ FORMS
from .models import (
    User, ElevProfile, ProfesorProfile, 
    Materie, Lectie, MaterialDidactic
)

# --- 1. Admin pentru User și Profile ---
# ... (codul pentru CustomUserAdmin și ProfileInlines rămâne neschimbat) ...
class ElevProfileInline(admin.StackedInline):
    model = ElevProfile
    can_delete = False
    verbose_name_plural = 'Profil Elev'

class ProfesorProfileInline(admin.StackedInline):
    model = ProfesorProfile
    can_delete = False
    verbose_name_plural = 'Profil Profesor'

class CustomUserAdmin(UserAdmin):
    inlines = (ElevProfileInline, ProfesorProfileInline)
    list_display = ('username', 'first_name', 'last_name', 'rol', 'is_staff')
    list_filter = UserAdmin.list_filter + ('rol',)
    fieldsets = UserAdmin.fieldsets + (
        ('Informații Suplimentare', {'fields': ('rol', 'numar_telefon')}),
    )

if admin.site.is_registered(User):
    admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# --- 2. Admin pentru Materii, Lecții și Materiale (CU WORKAROUND) ---

class MaterialDidacticInline(admin.StackedInline):
    model = MaterialDidactic
    extra = 1 
    verbose_name = "Material Didactic"
    verbose_name_plural = "Materiale Didactice"

@admin.register(Lectie)
class LectieAdmin(admin.ModelAdmin):
    list_display = ('titlu', 'materie', 'get_an_studiu_display')
    list_filter = ('an_studiu', 'materie')
    search_fields = ('titlu', 'materie__nume')
    inlines = [MaterialDidacticInline] 

    class Meta:
       model = Lectie

class LectieInline(admin.StackedInline):
    model = Lectie
    extra = 1
    verbose_name = "Lecție"
    verbose_name_plural = "Lecții"

@admin.register(Materie)
class MaterieAdmin(admin.ModelAdmin):
    list_display = ('nume',)
    search_fields = ('nume',)
    inlines = [LectieInline] 

# --- AICI ESTE WORKAROUND-UL ---
# 1. Creăm un formular customizat pentru MaterialDidactic
class MaterialDidacticAdminForm(forms.ModelForm):
    class Meta:
        model = MaterialDidactic
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        # 2. Suprascriem formularul
        super().__init__(*args, **kwargs)
        # 3. Aplicăm filtrul pentru 'autor' aici, în loc de models.py
        self.fields['autor'].queryset = User.objects.filter(rol=User.Rol.PROFESOR)


@admin.register(MaterialDidactic)
class MaterialDidacticAdmin(admin.ModelAdmin):
    # 4. Spunem adminului să folosească formularul nostru customizat
    form = MaterialDidacticAdminForm 
    
    list_display = ('titlu', 'lectie', 'autor', 'fisier')
    list_filter = ('lectie__materie', 'lectie__an_studiu', 'autor')
    search_fields = ('titlu', 'lectie__titlu')