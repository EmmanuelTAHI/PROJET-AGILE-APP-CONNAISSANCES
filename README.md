# Projet Agile — Installation & démarrage

Ce dépôt est une application Django (SQLite) avec Tailwind CSS + DaisyUI gérés via `npm`.

Prérequis
- Python 3.10+ (recommandé 3.11)
- Node.js + npm
- Sur Windows, installez les Build Tools si `Pillow` échoue (Visual C++). Installer `libjpeg`/libpng si besoin.

Installation (développement)

1. Créez et activez un environnement virtuel

   Windows (PowerShell)

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Mettre pip à jour et installer les dépendances Python

   ```powershell
   python -m pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   ```

3. Installer les dépendances Node (Tailwind + DaisyUI sont déjà dans `package.json`)

   ```bash
   npm install
   ```

4. Construire les CSS Tailwind

   - Construction de production (minifiée) :

     ```bash
     npm run build:css
     ```

   - Mode développement (recompilation automatique) :

     ```bash
     npm run watch:css
     ```

   Les sources Tailwind sont dans `assets/css/input.css` et le CSS compilé est généré dans `static/css/app.css`.

5. Préparer la base de données

   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. (Optionnel) Créer des données d'exemple

   ```bash
   python manage.py loaddata initial_data.json  # si vous avez un fixture
   # ou utiliser les commandes de gestion fournies
   python manage.py populate_data
   ```

7. Lancer le serveur de développement

   ```bash
   python manage.py runserver
   ```

Notes importantes
- Les fichiers médias sont servis depuis le dossier `media/` (défini dans `projet/settings.py`).
- Les identifiants SMTP et la `SECRET_KEY` sont en clair dans `projet/settings.py` pour le développement — pour la production, utiliser des variables d'environnement.
- `Pillow` est requis pour les champs `ImageField` — si l'installation échoue, installez les dépendances système (libjpeg, zlib) puis réessayez.
- `tailwindcss` et `daisyui` sont des dépendances `npm` (dev). Vous n'avez pas besoin de les ajouter dans `requirements.txt`.

Commandes utiles
- Tests : `python manage.py test`
- Collecte des fichiers statiques (production) : `python manage.py collectstatic --noinput`

Si vous souhaitez, je peux :
- pinner des versions plus précises des paquets Python,
- ajouter un `Makefile` ou des scripts pour Windows/Unix pour automatiser l'installation,
- ou préparer un `docker-compose` pour faciliter le déploiement.
