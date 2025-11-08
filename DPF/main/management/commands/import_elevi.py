# DPF/main/management/commands/import_elevi.py

import csv
import string
import random
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from main.models import User, ElevProfile

class Command(BaseCommand):
    help = 'Importă elevi dintr-un fișier CSV pentru o clasă specifică.'

    def add_arguments(self, parser):
        # Argumente pentru comanda:
        # 1. Anul (ex: 9)
        # 2. Litera (ex: C)
        # 3. Calea către fișier (ex: clasa_9c.csv)
        parser.add_argument('an_studiu', type=int, help='Anul de studiu (ex: 9, 10, 11, 12)')
        parser.add_argument('clasa_litera', type=str, help='Litera clasei (ex: A, B, C)')
        parser.add_argument('file_path', type=str, help='Calea către fișierul CSV')

    def generate_username(self, last_name, first_name):
        """Generează un username unic, ex: popescu.ion"""
        base_username = f"{last_name.lower().strip().replace(' ', '')}.{first_name.lower().strip().replace(' ', '')}"
        username = base_username
        count = 1
        # Verifică dacă userul există deja și adaugă un număr dacă e cazul
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{count}"
            count += 1
        return username

    def generate_password(self, length=10):
        """Generează o parolă temporară simplă"""
        # Poți face parola mai complexă dacă dorești
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for i in range(length))

    @transaction.atomic  # Folosim o tranzacție: dacă un elev dă eroare, nu se creează niciunul
    def handle(self, *args, **options):
        an_studiu = options['an_studiu']
        clasa_litera = options['clasa_litera'].upper()
        file_path = options['file_path']
        
        # Validare rapidă a datelor primite
        if an_studiu not in ElevProfile.AnStudiu.values:
            raise CommandError(f"Anul de studiu '{an_studiu}' este invalid. Alegeți din: {ElevProfile.AnStudiu.labels}.")
            
        if clasa_litera not in ElevProfile.LiteraClasa.values:
            raise CommandError(f"Litera '{clasa_litera}' este invalidă. Alegeți din: {ElevProfile.LiteraClasa.labels}.")

        self.stdout.write(self.style.SUCCESS(f"--- Începe importul pentru clasa {an_studiu}{clasa_litera} ---"))
        
        parole_generate = [] # Stocăm parolele pentru a le afișa la final

        try:
            with open(file_path, mode='r', encoding='utf-8') as file:
                # Presupunem un CSV cu formatul: Nume,Prenume
                reader = csv.reader(file)
                
                # Oprim header-ul (prima linie), dacă există
                next(reader, None)  

                for row in reader:
                    if not row: # Ignoră rândurile goale
                        continue
                        
                    try:
                        last_name = row[0].strip()
                        first_name = row[1].strip()

                        if not last_name or not first_name:
                            self.stdout.write(self.style.WARNING(f"Rând invalid (gol): {row}"))
                            continue

                        # 1. Generează datele
                        username = self.generate_username(last_name, first_name)
                        password = self.generate_password()

                        # 2. Creează User-ul
                        user = User.objects.create_user(
                            username=username,
                            password=password,
                            first_name=first_name,
                            last_name=last_name,
                            rol=User.Rol.ELEV # Rolul este setat automat
                        )

                        # 3. Creează Profilul de Elev
                        ElevProfile.objects.create(
                            user=user,
                            an_studiu=an_studiu,
                            clasa_litera=clasa_litera
                        )
                        
                        parole_generate.append((username, password, f"{last_name} {first_name}"))
                        self.stdout.write(self.style.SUCCESS(f"SUCCESS: Cont creat pentru {username} ({last_name} {first_name})"))

                    except Exception as e:
                         self.stdout.write(self.style.ERROR(f"Eroare la rândul {row}: {e}"))
                         # Datorită @transaction.atomic, dacă apare o eroare aici,
                         # nicio modificare din acest fișier nu va fi salvată.

        except FileNotFoundError:
            raise CommandError(f"Fișierul '{file_path}' nu a fost găsit.")
        except Exception as e:
            raise CommandError(f"O eroare neașteptată a apărut: {e}")

        self.stdout.write(self.style.SUCCESS(f"\n--- Import finalizat pentru clasa {an_studiu}{clasa_litera} ---"))
        self.stdout.write(self.style.WARNING("\nCredentiale temporare (salvează-le și distribuie-le în siguranță):"))
        for username, password, nume_complet in parole_generate:
            self.stdout.write(f"Elev: {nume_complet} | Username: {username} | Parola: {password}")