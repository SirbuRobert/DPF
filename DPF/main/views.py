from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import MaterialDidactic, User, ElevProfile, ProfesorProfile
from .forms import CustomUserCreationForm, ElevProfileForm, ProfesorProfileForm

# --- 1. View-ul pentru Homepage (Acasă) ---
def home_view(request):
    """
    Afișează pagina principală.
    Logica diferă dacă utilizatorul este logat sau nu.
    """
    if request.user.is_authenticated:
        # --- Utilizator LOGAT (Design-ul 'home page - logged in.png') ---
        context = {
            'materiale_recente': [] # Golește lista momentan
        }
        
        # Logica pt a prelua materiale (similară cu vechiul dashboard)
        try:
            if request.user.rol == User.Rol.ELEV:
                an_elev = request.user.elev_profile.an_studiu
                materiale = MaterialDidactic.objects.filter(an_studiu=an_elev)[:5] # Ultimele 5
                context['materiale_recente'] = materiale
                
            elif request.user.rol == User.Rol.PROFESOR:
                materiale = MaterialDidactic.objects.filter(autor=request.user)[:5] # Ultimele 5
                context['materiale_recente'] = materiale
        except (ElevProfile.DoesNotExist, ProfesorProfile.DoesNotExist):
            # Profilul nu e completat, dar e ok
            pass 
            
        return render(request, 'main/home.html', context)
    
    else:
        # --- Utilizator NELOGAT (Design-ul 'home page.png') ---
        # Doar afișăm pagina publică
        return render(request, 'main/home.html', {})

# --- 2. View-ul pentru Înregistrare (Create Account) ---
def register_view(request):
    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        elev_form = ElevProfileForm(request.POST)
        prof_form = ProfesorProfileForm(request.POST)
        
        if user_form.is_valid():
            user = user_form.save() # Salvăm utilizatorul
            
            # Acum, salvăm profilul corect
            try:
                if user.rol == User.Rol.ELEV:
                    if elev_form.is_valid():
                        elev_profile = elev_form.save(commit=False)
                        elev_profile.user = user # Setăm legătura
                        elev_profile.save()
                    else:
                        # Dacă formularul de elev e invalid, aruncăm o eroare
                        raise forms.ValidationError("Datele de elev sunt invalide.")

                elif user.rol == User.Rol.PROFESOR:
                    if prof_form.is_valid():
                        prof_profile = prof_form.save(commit=False)
                        prof_profile.user = user # Setăm legătura
                        prof_profile.save()
                    else:
                        # Dacă formularul de profesor e invalid, aruncăm o eroare
                        raise forms.ValidationError("Datele de profesor sunt invalide.")
                
                # Dacă totul a mers bine, logăm utilizatorul și îl trimitem acasă
                login(request, user)
                messages.success(request, "Cont creat cu succes!")
                return redirect('home')

            except Exception as e:
                # Dacă a apărut o eroare (de ex. profil invalid), ștergem userul creat
                user.delete()
                messages.error(request, f"Eroare la crearea profilului: {e}")

    else:
        # Dacă e GET, creăm formulare goale
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
    # Aici vei afișa pagina de profil (design-ul 'Profil.png')
    return render(request, 'main/profil.html', {})

@login_required
def materii_view(request):
    # Aici vei afișa pagina cu *toate* materialele
    # (Logica e similară cu cea din home_view, dar fără '[:5]')
    context = {}
    try:
        if request.user.rol == User.Rol.ELEV:
            an_elev = request.user.elev_profile.an_studiu
            materiale = MaterialDidactic.objects.filter(an_studiu=an_elev)
            context['materiale'] = materiale
        elif request.user.rol == User.Rol.PROFESOR:
            materiale = MaterialDidactic.objects.filter(autor=request.user)
            context['materiale'] = materiale
    except (ElevProfile.DoesNotExist, ProfesorProfile.DoesNotExist):
        pass

    return render(request, 'main/materii.html', context)