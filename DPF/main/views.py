# DPF/main/views.py
import json
import os
import tempfile
import re
from pathlib import Path

from PyPDF2 import PdfReader
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required # Importat o singură dată
from django.db import transaction
from django import forms # Necesar pentru 'raise forms.ValidationError'
from Ai.ai_pipeline import run_full_pipeline  # adjust import
from .models import MaterialDidactic, User, ElevProfile, ProfesorProfile, Lectie, Mesaj # Adaugă Mesaj
from django.db.models import Q, Count, Max  # Asigură-te că Q este importat
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


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
    user = request.user
    elev_profile = None
    profesor_profile = None
    cod_quiz_completat = False

    # În funcție de rolul userului, luăm profilul corect
    if user.rol == User.Rol.ELEV:
        try:
            elev_profile = ElevProfile.objects.get(user=user)
            cod_quiz_completat = bool(elev_profile.cod_quiz)
        except ElevProfile.DoesNotExist:
            pass

    elif user.rol == User.Rol.PROFESOR:
        try:
            profesor_profile = ProfesorProfile.objects.get(user=user)
        except ProfesorProfile.DoesNotExist:
            pass

    context = {
        'user': user,
        'elev_profile': elev_profile,
        'profesor_profile': profesor_profile,
        'cod_quiz_completat': cod_quiz_completat,
    }

    if request.method == 'POST' and 'poza_profil' in request.FILES:
        elev_profile.poza_profil = request.FILES['poza_profil']
        elev_profile.save()
        messages.success(request, "Poza a fost actualizată cu succes!")
        return redirect('profil')


    return render(request, 'main/profil.html', context)

    
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

@login_required # Accesibil doar utilizatorilor logați
def material_text_view(request, pk):
    def clean_extracted_text(raw: str) -> str:
        # 1) normalize newlines/spaces
        t = raw.replace("\r\n", "\n").replace("\r", "\n")
        t = t.replace("\u00a0", " ")  # NBSP -> space
        t = t.replace("\u200b", "")  # zero-width space

        # 2) fix hyphenation at line breaks: "infor-\nmation" -> "information"
        t = re.sub(r'(?<=\w)[\----‐­]\n(?=\w)', '', t)  # includes soft-hyphen variants

        # 3) protect list items & headings so we don't collapse their line breaks
        # mark newlines before bullets / numbered items / all-caps headings
        t = re.sub(r'\n(?=\s*(?:[\-\*\u2022]|[0-9]{1,2}\.)\s+)', '⏎', t)

        # 4) merge single line-breaks inside paragraphs into spaces (keep blank lines)
        t = re.sub(r'(?<!\n)\n(?!\n)', ' ', t)

        # 5) restore protected newlines
        t = t.replace('⏎', '\n')

        # 6) collapse multiple spaces/tabs and excessive blank lines
        t = re.sub(r'[ \t]{2,}', ' ', t)
        t = re.sub(r'\n{3,}', '\n\n', t)

        # 7) tidy spacing around punctuation
        t = re.sub(r'\s+([,.;:?!])', r'\1', t)
        t = re.sub(r'\(\s+', '(', t)
        t = re.sub(r'\s+\)', ')', t)

        return t.strip()
    material = get_object_or_404(MaterialDidactic.objects.select_related("lectie", "lectie__materie", "autor"),pk=pk,)

    # Access control similar to your materii_view
    if request.user.rol == User.Rol.ELEV:
        try:
            an_elev = request.user.elev_profile.an_studiu
        except ElevProfile.DoesNotExist:
            raise Http404()
        if material.lectie.an_studiu != an_elev:
            raise Http404()
    elif request.user.rol == User.Rol.PROFESOR:
        if material.autor_id != request.user.id:
            raise Http404()

    text = _extract_text_from_pdf_path(material.fisier.path)
    text = clean_extracted_text(text)

    return render(request, "main/material_text.html", {
        "material": material,
        "text": text,
    })

def api_summarize_selection(request):
    def _shorten(text: str, max_chars: int = 8000) -> str:
        if len(text) <= max_chars:
            return text
        # try to cut at sentence boundary
        cut = text[:max_chars]
        last = max(cut.rfind('. '), cut.rfind('! '), cut.rfind('? '))
        return cut[: last + 1 if last != -1 else max_chars]
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Payload invalid."}, status=400)

    raw_text = (payload.get("text") or "").strip()
    locale = (payload.get("locale") or "ro").strip().lower()
    if not raw_text:
        return JsonResponse({"error": "Lipsește textul de rezumat."}, status=400)

    def _get_nested(obj, path: str):
        cur = obj
        for part in path.split("."):
            cur = getattr(cur, part, None)
            if cur is None:
                return None
        return cur

    def _get_user_cod_quiz(user) -> str | None:
        # Adjust these to match where you store it
        candidates = [
            "cod_quiz",
            "quiz_string",
            "prompt_hint",
            "elev_profile.cod_quiz",
            "profesor_profile.cod_quiz",
            "profile.cod_quiz",
        ]
        for path in candidates:
            val = _get_nested(user, path)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return None

    # keep request small
    text = _shorten(raw_text, max_chars=8000)

    cod_quiz = _get_user_cod_quiz(request.user)
    if not cod_quiz:
        # Fallback instruction if the user hasn’t set one
        cod_quiz = "Oferă un răspuns scurt și clar bazat pe selecția de mai jos."

    # choose the token (API key): prefer per-user stored key, fallback to settings
    def env_required(name: str) -> str:
        val = os.getenv(name)
        if not val:
            raise ImproperlyConfigured(f"Missing required environment variable: {name}")
        return val
    api_key = env_required("MY_API_KEY")
    if not api_key:
        return JsonResponse({"error": "Cheia OpenAI nu este configurată pe server."}, status=500)

    # --- OpenAI call ---
    try:
        # Works with the OpenAI Python SDK v1.x
        client = OpenAI(api_key=api_key)

        system_msg = (
            "You are a helpful assistant that writes short, faithful explanations. "
            "Keep key terms, equations, and definitions; remove fluff. "
            "Length: ~4-6 concise bullet points or 3-5 sentences. "
            f"Language: {'Romanian' if locale.startswith('ro') else 'English'}."
        )

        user_msg = (
            f"{cod_quiz}\n\n"
            f"<text>\n{text}\n</text>"
        )

        # fast + affordable model; adjust to your account
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        summary = completion.choices[0].message.content.strip()

        return JsonResponse({"summary": summary})
    except Exception as e:
        return JsonResponse({"error": f"Eroare la apelul OpenAI: {e}"}, status=500)


@login_required
def profesori_view(request):
    """
    Afișează lista de profesori pentru ELEVI sau lista de elevi pentru PROFESORI.
    """
    context = {}
    
    if request.user.rol == User.Rol.ELEV:
        # LOGICA EXISTENTĂ: ELEVUL VEDE PROFESORII
        
        profesori_qs = (
            ProfesorProfile.objects
            .select_related('user', 'materie_predata')
            .filter(user__rol=User.Rol.PROFESOR)
            .order_by('user__last_name', 'user__first_name')
        )
        
        profesori_la_clasa = []
        restul_profesorilor = list(profesori_qs)

        try:
            elev_profile = request.user.elev_profile
            an_studiu = elev_profile.an_studiu

            profesori_relevanti_ids = MaterialDidactic.objects.filter(
                lectie__an_studiu=an_studiu
            ).values_list('autor_id', flat=True).distinct()

            profesori_la_clasa = []
            restul_profesorilor = []
            
            for prof_profile in profesori_qs:
                if prof_profile.user.id in profesori_relevanti_ids:
                    profesori_la_clasa.append(prof_profile)
                else:
                    restul_profesorilor.append(prof_profile)

        except ElevProfile.DoesNotExist:
            pass
            
        context['lista_tip'] = 'PROFESORI'
        context['profesori_la_clasa'] = profesori_la_clasa
        context['restul_profesorilor'] = restul_profesorilor
        
    elif request.user.rol == User.Rol.PROFESOR:
        # LOGICA NOUĂ: PROFESORUL VEDE ELEVII

        elevi_qs = (
            ElevProfile.objects
            .select_related('user')
            .filter(user__rol=User.Rol.ELEV)
            .order_by('user__last_name', 'user__first_name')
        )

        elevi_la_clasele_mele = []
        restul_elevilor = list(elevi_qs)

        try:
            profesor_profile = request.user.profesor_profile
            # Presupunem că profesorul predă materia asociată la toate clasele unde există acea materie
            # Alternativ, am putea folosi materialele încărcate de el pentru a filtra elevii, similar cu logica de sus
            
            # EXEMPLU: Filtrare bazată pe materialele încărcate de profesor
            anii_predati = Lectie.objects.filter(
                materie=profesor_profile.materie_predata,
                materiale__autor=request.user
            ).values_list('an_studiu', flat=True).distinct()
            
            elevi_la_clasele_mele = []
            restul_elevilor = []
            
            for elev_profile in elevi_qs:
                if elev_profile.an_studiu in anii_predati:
                    elevi_la_clasele_mele.append(elev_profile)
                else:
                    restul_elevilor.append(elev_profile)

        except ProfesorProfile.DoesNotExist:
            pass # Nu ar trebui să se întâmple dacă rolul este Profesor

        context['lista_tip'] = 'ELEVI'
        context['elevi_la_clasele_mele'] = elevi_la_clasele_mele
        context['restul_elevilor'] = restul_elevilor
        
    else:
        # Pentru admini sau alte roluri, putem afișa o pagină goală sau o eroare 403
        return redirect('home') 

    # Redirecționăm către un șablon care poate gestiona ambele liste
    return render(request, 'main/lista_utilizatorilor.html', context)

@login_required
def chat_view(request, destinatar_id):
    expeditor = request.user
    destinatar = get_object_or_404(User, pk=destinatar_id)

    # Filtrăm mesajele care sunt fie (Expeditor -> Destinatar) SAU (Destinatar -> Expeditor)
    mesaje = Mesaj.objects.filter(
        Q(expeditor=expeditor, destinatar=destinatar) |
        Q(expeditor=destinatar, destinatar=expeditor)
    ).order_by('data_trimitere')

    if request.method == 'POST':
        continut = request.POST.get('continut')
        if continut and continut.strip():
            # Crează și salvează noul mesaj
            Mesaj.objects.create(
                expeditor=expeditor,
                destinatar=destinatar,
                continut=continut.strip()
            )
            # Redirecționăm pentru a preveni re-trimiterea mesajului la refresh (POST/REDIRECT/GET)
            return redirect('chat', destinatar_id=destinatar_id)

    context = {
        'destinatar': destinatar,
        'mesaje': mesaje,
    }

    return render(request, 'main/chat.html', context)

@login_required
def get_messages_ajax_view(request, destinatar_id):
    """
    Returnează fragmentul HTML cu mesajele actuale pentru a fi folosit de AJAX.
    """
    expeditor = request.user
    destinatar = get_object_or_404(User, pk=destinatar_id)

    # Aceeași logică de filtrare ca în chat_view
    mesaje = Mesaj.objects.filter(
        Q(expeditor=expeditor, destinatar=destinatar) |
        Q(expeditor=destinatar, destinatar=expeditor)
    ).order_by('data_trimitere')

    # Rendăm doar fragmentul de șablon care conține mesajele
    return render(request, 'main/_chat_messages.html', {
        'mesaje': mesaje,
        'destinatar': destinatar,
        'user': request.user # Trecem user-ul pentru a determina expeditorul în șablon
    })

@login_required
def chat_inbox_view(request):
    """
    Afișează lista de utilizatori cu care utilizatorul curent a avut conversații recente.
    Permite căutarea de utilizatori noi.
    """
    user = request.user
    
    # 1. Găsirea utilizatorilor unici cu care s-a corespondat (SOLUȚIA PENTRU EROARE)
    
    # Obține ID-urile destinatarilor (cei cărora utilizatorul le-a trimis mesaje)
    destinatari_ids = Mesaj.objects.filter(expeditor=user).values_list('destinatar_id', flat=True)
    
    # Obține ID-urile expeditorilor (cei de la care utilizatorul a primit mesaje)
    expeditori_ids = Mesaj.objects.filter(destinatar=user).values_list('expeditor_id', flat=True)

    # Combină seturile de ID-uri (UNION este distinct automat)
    persoane_contactate_ids = destinatari_ids.union(expeditori_ids)
    
    # Preluăm obiectele User pentru persoanele contactate, excluzând utilizatorul curent.
    conversatii_recente = (
        User.objects
        .filter(pk__in=persoane_contactate_ids)
        .exclude(pk=user.pk)
        .order_by('last_name')
    )
    
    # 2. Logica de Căutare a Utilizatorilor
    termen_cautare = request.GET.get('q')
    utilizatori_gasiti = []
    
    if termen_cautare:
        utilizatori_gasiti = (
            User.objects
            .filter(
                Q(first_name__icontains=termen_cautare) | 
                Q(last_name__icontains=termen_cautare) |
                Q(username__icontains=termen_cautare)
            )
            # Excludem utilizatorul curent și pe cei care sunt deja în conversațiile recente
            .exclude(pk=user.pk)
            .exclude(pk__in=persoane_contactate_ids)
            .order_by('last_name')
        )

    context = {
        'conversatii_recente': conversatii_recente,
        'utilizatori_gasiti': utilizatori_gasiti,
        'termen_cautare': termen_cautare
    }
    
    return render(request, 'main/chat_inbox.html', context)