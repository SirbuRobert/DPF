# DPF/main/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings # Necesar pentru a lega la AUTH_USER_MODEL

# --- 1. Modelul User Customizat ---

class User(AbstractUser):
    """
    Modelul de bază pentru Utilizator.
    Extinde modelul standard Django (AbstractUser) pentru a adăuga rol
    și număr de telefon.
    """
    
    # Adăugăm câmpurile Nume și Prenume ca fiind obligatorii
    first_name = models.CharField(max_length=150, blank=False, verbose_name="Prenume")
    last_name = models.CharField(max_length=150, blank=False, verbose_name="Nume")

    # Facem emailul opțional și non-unic
    email = models.EmailField(blank=True, null=True, unique=False, verbose_name="Adresă email")

    # Câmpul nou pentru numărul de telefon
    numar_telefon = models.CharField(max_length=15, blank=True, verbose_name="Număr de telefon")

    # --- Definirea Rolurilor ---
    class Rol(models.TextChoices):
        ELEV = 'ELEV', 'Elev'
        PROFESOR = 'PROFESOR', 'Profesor'
        # Poți adăuga 'ADMIN' aici mai târziu

    rol = models.CharField(
        max_length=10,
        choices=Rol.choices,
        default=Rol.ELEV,
        verbose_name="Rol"
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"


# --- 2. Modelele "Profile" pentru fiecare Rol ---

class ElevProfile(models.Model):
    """
    Stochează datele specifice DOAR elevilor.
    """
    # Relație unu-la-unu cu modelul User
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='elev_profile' # Ne va ajuta să accesăm ușor (user.elev_profile)
    )

    # Definirea Alegerilor (Choices)
    class AnStudiu(models.IntegerChoices):
        CLASA_9 = 9, 'Clasa a 9-a'
        CLASA_10 = 10, 'Clasa a 10-a'
        CLASA_11 = 11, 'Clasa a 11-a'
        CLASA_12 = 12, 'Clasa a 12-a'
    
    class LiteraClasa(models.TextChoices):
        A = 'A', 'A'
        B = 'B', 'B'
        C = 'C', 'C'
        D = 'D', 'D'
        E = 'E', 'E'
        F = 'F', 'F'

    an_studiu = models.IntegerField(
        choices=AnStudiu.choices,
        verbose_name="An de studiu"
    )
    clasa_litera = models.CharField(
        max_length=2,
        choices=LiteraClasa.choices,
        verbose_name="Litera clasei"
    )

    def __str__(self):
        # Va afișa ceva de genul "Elev: popescu.ion - 9A"
        return f"Elev: {self.user.username} - {self.an_studiu}{self.clasa_litera}"


class ProfesorProfile(models.Model):
    """
    Stochează datele specifice DOAR profesorilor.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='profesor_profile' # Ne va ajuta să accesăm (user.profesor_profile)
    )
    
    # ❗ MODIFICAREA: Legătură către modelul Materie
    materie_predata = models.ForeignKey(
        'Materie', # Folosim string pt a evita erori de import circular
        on_delete=models.SET_NULL, # Dacă ștergem materia, profesorul rămâne
        null=True,
        blank=True,
        verbose_name="Materia predată"
    )

    def __str__(self):
        return f"Profesor: {self.user.username} - {self.materie_predata or 'N/A'}"

# --- 3. Modelele pentru Materii și Materiale ---

class Materie(models.Model):
    """
    Modelul de bază pentru o materie.
    Ex: "Matematică", "Istorie", "Limba Română"
    """
    nume = models.CharField(max_length=100, unique=True, verbose_name="Nume Materie")

    class Meta:
        verbose_name = "Materie"
        verbose_name_plural = "Materii"
        ordering = ['nume']

    def __str__(self):
        return self.nume


class MaterialDidactic(models.Model):
    """
    Materialul propriu-zis (lecție, fișier, video link etc.)
    Acesta este modelul central care leagă totul.
    """
    
    # --- Alegerile pentru Anul de Studiu (copiate de la ElevProfile) ---
    class AnStudiu(models.IntegerChoices):
        CLASA_9 = 9, 'Clasa a 9-a'
        CLASA_10 = 10, 'Clasa a 10-a'
        CLASA_11 = 11, 'Clasa a 11-a'
        CLASA_12 = 12, 'Clasa a 12-a'

    # --- Legăturile ---
    materie = models.ForeignKey(
        Materie, 
        on_delete=models.CASCADE, 
        related_name="materiale"
    )
    
    an_studiu = models.IntegerField(
        choices=AnStudiu.choices,
        verbose_name="An de studiu"
    )
    
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True,
        related_name="materiale_create",
        limit_choices_to={'rol': User.Rol.PROFESOR} # Doar profesorii pot fi autori
    )

    # --- Conținutul Efectiv ---
    titlu = models.CharField(max_length=255, verbose_name="Titlu")
    descriere = models.TextField(blank=True, verbose_name="Descriere / Conținut text")
    
    # Pentru upload de fișiere (Necesită MEDIA_ROOT și MEDIA_URL în settings.py)
    fisier = models.FileField(
        upload_to='materiale_didactice/%Y/%m/', 
        blank=True, 
        null=True,
        verbose_name="Fișier atașat"
    )
    
    data_adaugarii = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['materie', 'an_studiu', 'titlu']
        verbose_name = "Material Didactic"
        verbose_name_plural = "Materiale Didactice"

    def __str__(self):
        return f"{self.materie.nume} ({self.get_an_studiu_display()}) - {self.titlu}"