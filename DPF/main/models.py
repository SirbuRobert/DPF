# DPF/main/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings # Necesar pentru a lega la AUTH_USER_MODEL
from django.core.validators import FileExtensionValidator # IMPORTUL NECESAR PENTRU PDF

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


    cod_quiz = models.TextField(null=True, blank=True)

    poza_profil = models.ImageField(upload_to='poze_profil/', null=True, blank=True)
    
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
    
    # Legătură către modelul Materie
    materie_predata = models.ForeignKey(
        'Materie', # Folosim string pt a evita erori de import circular
        on_delete=models.SET_NULL, # Dacă ștergem materia, profesorul rămâne
        null=True,
        blank=True,
        verbose_name="Materia predată"
    )

    def __str__(self):
        return f"Profesor: {self.user.username} - {self.materie_predata or 'N/A'}"

# --- 3. Modelele pentru Materii, Lecții și Materiale ---

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

# --- MODEL NOU: LECTIE ---
class Lectie(models.Model):
    """
    Modelul pentru o lecție specifică (capitol).
    Leagă o Materie de un An de Studiu și un titlu.
    Ex: Istorie, Clasa a 9-a, "Primul Război Mondial"
    """
    
    # Alegerile pentru Anul de Studiu
    class AnStudiu(models.IntegerChoices):
        CLASA_9 = 9, 'Clasa a 9-a'
        CLASA_10 = 10, 'Clasa a 10-a'
        CLASA_11 = 11, 'Clasa a 11-a'
        CLASA_12 = 12, 'Clasa a 12-a'

    # --- Legăturile ---
    materie = models.ForeignKey(
        Materie, 
        on_delete=models.CASCADE, 
        related_name="lectii" # O materie are mai multe lecții
    )
    
    an_studiu = models.IntegerField(
        choices=AnStudiu.choices,
        verbose_name="An de studiu"
    )
    
    # --- Conținutul Efectiv ---
    titlu = models.CharField(max_length=255, verbose_name="Titlu Lecție")
    descriere_scurta = models.TextField(blank=True, verbose_name="Sumar Lecție")
    
    data_crearii = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['materie', 'an_studiu', 'titlu']
        verbose_name = "Lecție"
        verbose_name_plural = "Lecții"
        # Ne asigurăm că nu există 2 lecții cu același nume la aceeași materie/an
        unique_together = ['materie', 'an_studiu', 'titlu']

    def __str__(self):
        # Va afișa: "Istorie (Clasa a 9-a) - Primul Război Mondial"
        return f"{self.materie.nume} ({self.get_an_studiu_display()}) - {self.titlu}"



# --- MODEL MODIFICAT: MATERIAL DIDACTIC ---
class MaterialDidactic(models.Model):
    """
    Materialul propriu-zis (PDF, link etc.)
    Acum, acesta este legat de o LECȚIE.
    """
    
    # --- Legăturile MODIFICATE ---
    lectie = models.ForeignKey(
        Lectie,
        on_delete=models.CASCADE,
        related_name="materiale" # O lecție are mai multe materiale
    )
    
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True,
        related_name="materiale_create",
        limit_choices_to={'rol': User.Rol.PROFESOR} # Doar profesorii pot fi autori
    )

    # --- Conținutul Efectiv ---
    titlu = models.CharField(max_length=255, verbose_name="Titlu Material")
    descriere = models.TextField(blank=True, verbose_name="Descriere / Conținut text")
    
    fisier = models.FileField(
        upload_to='materiale_didactice/%Y/%m/', 
        blank=True, 
        null=True,
        verbose_name="Fișier atașat (doar PDF)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])] # <-- Validatorul e aici!
    )
    
    data_adaugarii = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['lectie', 'titlu']
        verbose_name = "Material Didactic"
        verbose_name_plural = "Materiale Didactice"

    def __str__(self):
        # Va afișa: "Primul Război Mondial - Rezumat.pdf"
        return f"{self.lectie.titlu} - {self.titlu}"

class Mesaj(models.Model):
    """
    Stochează un singur mesaj trimis între doi utilizatori.
    """
    expeditor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='mesaje_trimise',
        verbose_name="Expeditor"
    )
    destinatar = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='mesaje_primite',
        verbose_name="Destinatar"
    )
    continut = models.TextField(verbose_name="Conținutul mesajului")
    data_trimitere = models.DateTimeField(auto_now_add=True)
    citit = models.BooleanField(default=False)

    class Meta:
        ordering = ['data_trimitere']
        verbose_name = "Mesaj"
        verbose_name_plural = "Mesaje"

    def __str__(self):
        return f"De la {self.expeditor.username} către {self.destinatar.username} la {self.data_trimitere.strftime('%H:%M')}"
    
