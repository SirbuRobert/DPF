# DPF/main/views.py
import os
import tempfile

from PyPDF2 import PdfReader
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required # Importat o singură dată
from django.db import transaction
from django import forms # Necesar pentru 'raise forms.ValidationError'
from Ai.ai_pipeline import run_full_pipeline  # adjust import

# Importăm Modelele
from .models import MaterialDidactic, User, ElevProfile, ProfesorProfile, Lectie

# Importăm Formularele
from .forms import (
    CustomUserCreationForm, 
    ElevProfileForm, 
    ProfesorProfileForm, 
    ImportEleviForm
)

# Importuri pentru logica de import CSV
import csv
import io
import string
import random

# --- Funcții ajutătoare pentru generare conturi ---
# (Acestea stau aici, NU în interiorul altei funcții)

def generate_username(last_name, first_name):
    """Generează un username unic, ex: popescu.ion"""
    base_username = f"{last_name.lower().strip().replace(' ', '')}.{first_name.lower().strip().replace(' ', '')}"
    username = base_username
    count = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{count}"
        count += 1
    return username

def generate_password(length=10):
    """Generează o parolă temporară simplă"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for i in range(length))


# --- 1. View-ul pentru Homepage (Acasă) ---
def home_view(request):
    """
    Afișează pagina principală.
    Logica diferă dacă utilizatorul este logat sau nu.
    """
    if request.user.is_authenticated:
        context = {
            'materiale_recente': []
        }
        try:
            if request.user.rol == User.Rol.ELEV:
                an_elev = request.user.elev_profile.an_studiu
                materiale = MaterialDidactic.objects.filter(lectie__an_studiu=an_elev).order_by('-data_adaugarii')[:5]
                context['materiale_recente'] = materiale
                
            elif request.user.rol == User.Rol.PROFESOR:
                materiale = MaterialDidactic.objects.filter(autor=request.user).order_by('-data_adaugarii')[:5]
                context['materiale_recente'] = materiale
        except (ElevProfile.DoesNotExist, ProfesorProfile.DoesNotExist):
            pass 
            
        return render(request, 'main/home.html', context)
    
    else:
        return render(request, 'main/home.html', {})

# --- 2. View-ul pentru Înregistrare (Create Account) ---
def register_view(request):
    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        elev_form = ElevProfileForm(request.POST)
        prof_form = ProfesorProfileForm(request.POST)
        
        if user_form.is_valid():
            user = user_form.save() 
            
            try:
                if user.rol == User.Rol.ELEV:
                    if elev_form.is_valid():
                        elev_profile = elev_form.save(commit=False)
                        elev_profile.user = user 
                        elev_profile.save()
                    else:
                        raise forms.ValidationError(f"Datele de elev sunt invalide: {elev_form.errors.as_text()}")

                elif user.rol == User.Rol.PROFESOR:
                    if prof_form.is_valid():
                        prof_profile = prof_form.save(commit=False)
                        prof_profile.user = user 
                        prof_profile.save()
                    else:
                        raise forms.ValidationError(f"Datele de profesor sunt invalide: {prof_form.errors.as_text()}")
                
                login(request, user)
                messages.success(request, "Cont creat cu succes!")
                return redirect('home')

            except Exception as e:
                user.delete()
                messages.error(request, f"Eroare la crearea profilului: {e}")

    else:
        user_form = CustomUserCreationForm()
        elev_form = ElevProfileForm()
        prof_form = ProfesorProfileForm()

    return render(request, 'main/register.html', {
        'user_form': user_form,
        'elev_form': elev_form,
        'prof_form': prof_form
    })

# --- 3. View-ul pentru Login ---
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"Te-ai conectat ca {username}.")
                return redirect('home')
            else:
                messages.error(request, "Username sau parolă invalidă.")
        else:
            messages.error(request, "Username sau parolă invalidă.")
    else:
        form = AuthenticationForm()
        
    return render(request, 'main/login.html', {'login_form': form})

# --- 4. View-ul pentru Logout ---
def logout_view(request):
    logout(request)
    messages.info(request, "Ai fost deconectat.")
    return redirect('home')

# --- 5. View-uri Stub (pe care le vei dezvolta) ---
@login_required
def profil_view(request):
    return render(request, 'main/profil.html', {})

@login_required
@login_required
def materii_view(request):
    context = {}
    try:
        if request.user.rol == User.Rol.ELEV:
            an_elev = request.user.elev_profile.an_studiu
            materiale = (
                MaterialDidactic.objects
                .select_related("lectie", "lectie__materie", "autor")
                .filter(lectie__an_studiu=an_elev)            # <-- HERE
                .order_by("-data_adaugarii")
            )
            context["materiale"] = materiale

        elif request.user.rol == User.Rol.PROFESOR:
            materiale = (
                MaterialDidactic.objects
                .select_related("lectie", "lectie__materie", "autor")
                .filter(autor=request.user)
                .order_by("-data_adaugarii")
            )
            context["materiale"] = materiale
    except (ElevProfile.DoesNotExist, ProfesorProfile.DoesNotExist):
        pass

    return render(request, "main/materii.html", context)


# --- 6. View-ul pentru Import Elevi (din interfața web) ---
@staff_member_required # Doar utilizatorii cu is_staff=True pot accesa
def import_elevi_view(request):
    """
    Pagină web pentru a încărca un CSV și a crea conturi de elevi.
    """
    parole_generate = [] # Lista unde vom stoca parolele

    if request.method == 'POST':
        form = ImportEleviForm(request.POST, request.FILES)
        
        if form.is_valid():
            an_studiu = form.cleaned_data['an_studiu']
            clasa_litera = form.cleaned_data['clasa_litera']
            fisier_csv = form.cleaned_data['fisier_csv']
            
            try:
                with transaction.atomic():
                    fisier_text = io.StringIO(fisier_csv.read().decode('utf-8'))
                    reader = csv.reader(fisier_text)
                    
                    next(reader, None) # Sărim peste header

                    for row in reader:
                        if not row: continue 
                        
                        try:
                            last_name = row[0].strip()
                            first_name = row[1].strip()

                            if not last_name or not first_name:
                                messages.warning(request, f"Rând invalid (ignorat): {row}")
                                continue

                            username = generate_username(last_name, first_name)
                            password = generate_password()

                            user = User.objects.create_user(
                                username=username,
                                password=password,
                                first_name=first_name,
                                last_name=last_name,
                                rol=User.Rol.ELEV
                            )

                            ElevProfile.objects.create(
                                user=user,
                                an_studiu=an_studiu,
                                clasa_litera=clasa_litera
                            )
                            
                            parole_generate.append((username, password, f"{last_name} {first_name}"))

                        except Exception as e:
                            raise Exception(f"Eroare la procesarea rândului {row}: {e}")

                messages.success(request, f"Import reușit! Au fost create {len(parole_generate)} conturi pentru clasa {an_studiu}{clasa_litera}.")
            
            except UnicodeDecodeError:
                messages.error(request, "Eroare: Fișierul nu pare a fi codat în UTF-8. Salvează-l ca 'CSV (UTF-8)'.")
            except Exception as e:
                messages.error(request, f"Importul a eșuat. Niciun cont nu a fost creat. Detaliu: {e}")

    else:
        form = ImportEleviForm()

    return render(request, 'main/import_elevi.html', {
        'form': form,
        'parole_generate': parole_generate
    })

#view quiz, ala de personalitate
def quiz_view(request):
    quiz = [
        {
            'id': 1,
            'text': 'Cum preferi sa inveti?',
            'optiuni': [
                ('Explica-mi ca unui copil de liceu, fară să menționezi asta, si oferă-mi exerciții practice,', 'Incerc sa învăț prin practică'),
                ('Explica-mi ca unui copil de liceu, fară să menționezi asta, si ofera-mi multe exemple', 'Prin multe exemple'),
                ('Explica-mi ca unui copil de liceu, fară să menționezi asta, si oferă-mi teorie', 'Prin citirea teoriei')
                
            ]
        },
        {
            'id': 2,
            'text': 'Cum preferi să ti se explice cand nu intelegi ceva?',
            'optiuni': [
                ('explicandu-mi pas cu pas', 'Vreau solutia integrala si sa invat pe baza ei'),
                ('dandu-mi mici hinturi, nu raspunsul complet', 'Vreau doar mici indicii'),
                ('Spunandu-mi doar unde sa caut informatii', 'Vreau sa caut singur informatii')
            ]
        },
        {
            'id': 3,
            'text': 'Cum preferi să fie structurat conținutul atunci când înveți ceva nou?',
            'optiuni': [
                ('Organizează explicațiile într-o structură clară, cu pași numerotați și concluzii la final.', 'Prin pași clari și concluzii'),
                ('Prezintă ideile liber, dar cu exemple care curg natural una din alta.', 'Prin poveste liberă și exemple'),
                ('Rezumă totul la esențial, evitând detaliile tehnice inutile.', 'Prin rezumate scurte și clare')
            ]
        }
    ]

    if request.method == 'POST':
        coduri = []
        for q in quiz:
            cod = request.POST.get(f"q_{q['id']}")
            if cod:
                coduri.append(cod)

        cod_final = ' '.join(coduri)

        # Salvăm rezultatul în Student
        student = ElevProfile.objects.get(user=request.user)
        student.cod_quiz = cod_final
        student.save()

        return render(request, 'main/quiz.html', {'cod': cod_final, 'quiz': quiz})

    return render(request, 'main/quiz.html', {'quiz': quiz})


def _extract_text_from_pdf_path(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def lectie_ai_view(request, lectie_id: int):
    lectie = get_object_or_404(Lectie, pk=lectie_id)

    # pick the most recent PDF for this lesson
    material = (
        MaterialDidactic.objects
        .filter(lectie=lectie, fisier__isnull=False)
        .order_by("-data_adaugarii")
        .first()
    )
    if not material:
        return render(request, "main/lectie_ai.html", {
            "lectie": lectie,
            "error": "Nu există niciun fișier PDF asociat acestei lecții."
        })

    pdf_path = material.fisier.path  # local storage ⇒ this works

    # If your pipeline ALREADY accepts PDFs, you can do:
    # result = run_full_pipeline(pdf_path, num_questions=7, max_tokens_summ=150)

    # Otherwise: extract text → write to a temp .txt → call run_full_pipeline(path_to_txt)
    text = _extract_text_from_pdf_path(pdf_path)
    if not text.strip():
        return render(request, "main/lectie_ai.html", {
            "lectie": lectie,
            "material": material,
            "error": "PDF-ul pare gol sau scanat (fără text). Pentru PDF-uri scanate ai nevoie de OCR."
        })

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
        tmp.write(text)
        tmp_path = tmp.name

    try:
        result = run_full_pipeline(tmp_path, num_questions=7, max_tokens_summ=150)
    finally:
        try: os.unlink(tmp_path)
        except OSError: pass

    quiz_raw = result.get("quiz_results") or []

    # normalize keys
    quiz = []
    for item in quiz_raw:
        quiz.append({
            **item,
            "question": item.get("question") or item.get("question_text") or "",
            "answer": item.get("answer") or item.get("answer_text") or "",
        })

    if not result:
        return render(request, "main/lectie_ai.html", {
            "lectie": lectie,
            "material": material,
            "error": "Procesarea nu a returnat rezultat."
        })

    return render(request, "main/lectie_ai.html", {
        "lectie": lectie,
        "material": material,
        "summary": result.get("final_summary", ""),
        "quiz": quiz,  # <— normalized
        "lang": result.get("original_lang", "en"),
    })