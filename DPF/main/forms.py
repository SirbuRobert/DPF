# DPF/main/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, ElevProfile, ProfesorProfile, Materie

# --- 1. Formularul de Înregistrare Customizat ---
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'rol', 'numar_telefon') # Am adăugat câmpurile noi
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Setăm câmpurile first_name și last_name ca fiind obligatorii
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

# --- 2. Formularul pentru Profilul Elevului ---
class ElevProfileForm(forms.ModelForm):
    class Meta:
        model = ElevProfile
        fields = ['an_studiu', 'clasa_litera']

# --- 3. Formularul pentru Profilul Profesorului ---
class ProfesorProfileForm(forms.ModelForm):
    # Facem câmpul să afișeze materiile sortate alfabetic
    materie_predata = forms.ModelChoiceField(
        queryset=Materie.objects.all().order_by('nume'),
        required=False,
        label="Materia predată"
    )

    class Meta:
        model = ProfesorProfile
        fields = ['materie_predata']

# --- 4. Formularul pentru Import Elevi ---
class ImportEleviForm(forms.Form):
    """
    Formular pentru a selecta clasa și a încărca un fișier CSV.
    """
    an_studiu = forms.ChoiceField(
        choices=ElevProfile.AnStudiu.choices,
        label="Selectează anul"
    )
    clasa_litera = forms.ChoiceField(
        choices=ElevProfile.LiteraClasa.choices,
        label="Selectează litera"
    )
    fisier_csv = forms.FileField(
        label="Selectează fișierul CSV",
        help_text="Fișierul trebuie să conțină coloanele 'Nume' și 'Prenume'"
    )

    def clean_fisier_csv(self):
        """Verifică dacă fișierul este de tip CSV."""
        fisier = self.cleaned_data.get('fisier_csv')
        if fisier:
            if not fisier.name.endswith('.csv'):
                raise forms.ValidationError("Fișierul trebuie să aibă extensia .csv")
        return fisier