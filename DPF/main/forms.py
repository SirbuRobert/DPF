from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, ElevProfile, ProfesorProfile, Materie

class CustomUserCreationForm(UserCreationForm):
    """
    Un formular de creare a utilizatorului care include
    Nume, Prenume și Rol.
    """
    first_name = forms.CharField(max_length=150, required=True, label="Prenume")
    last_name = forms.CharField(max_length=150, required=True, label="Nume")
    
    # Adăugăm câmpul 'rol' ca radio buttons
    rol = forms.ChoiceField(
        choices=User.Rol.choices,
        widget=forms.RadioSelect,
        label="Sunt:"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        # Extindem câmpurile pentru a le include pe ale noastre
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'rol')

class ElevProfileForm(forms.ModelForm):
    """Formular pentru a colecta datele elevului la înregistrare."""
    class Meta:
        model = ElevProfile
        fields = ['an_studiu', 'clasa_litera']
        labels = {
            'an_studiu': 'Anul de studiu',
            'clasa_litera': 'Litera clasei'
        }

class ProfesorProfileForm(forms.ModelForm):
    """Formular pentru a colecta datele profesorului la înregistrare."""
    materie_predata = forms.ModelChoiceField(
        queryset=Materie.objects.all(),
        required=True,
        label="Materia predată",
        empty_label="Selectează materia"
    )
    
    class Meta:
        model = ProfesorProfile
        fields = ['materie_predata']