# Deploying NIT Store to PythonAnywhere (nit.pythonanywhere.com or nabil371.pythonanywhere.com)

---

## 📌 How PythonAnywhere Subdomains Work

On PythonAnywhere:
1. **Free Account Subdomain:** Every free account gets a subdomain matching its **username**: `https://<username>.pythonanywhere.com`.
   - If your account username is **`nit`**, your website address will be: **`https://nit.pythonanywhere.com`**
   - If your account username is **`Nabil371`**, your website address is: **`https://nabil371.pythonanywhere.com`**
2. **Paid Account (Hacker plan $5/mo):** Allows you to attach custom domains (e.g. `store.yourdomain.com`).

> **Both domains (`nit.pythonanywhere.com` and `nabil371.pythonanywhere.com`) are already pre-configured in `nit_home/settings.py`!** Whichever username you use on PythonAnywhere, the code works automatically.

---

## Step 1: Push the Latest Code to GitHub
On your local machine:
```bash
git add .
git commit -m "Support nit.pythonanywhere.com and nabil371.pythonanywhere.com"
git push origin master
```

---

## Step 2: Open PythonAnywhere Bash Console
1. Log in to [pythonanywhere.com](https://www.pythonanywhere.com).
2. Go to the **Consoles** tab and click **Bash**.

---

## Step 3: Clone or Pull the Project
In the PythonAnywhere Bash console:
```bash
# Navigate to home directory
cd ~

# If you haven't cloned yet:
git clone https://github.com/nabilmushfique460/NIT-Home-website---Django.git

# Enter the project folder:
cd NIT-Home-website---Django

# If already cloned, pull latest changes:
git pull origin master
```

---

## Step 4: Create and Configure Virtual Environment
Run in the Bash console:
```bash
# Create virtualenv with Python 3.10
mkvirtualenv --python=/usr/bin/python3.10 nit-env

# Activate virtualenv (if not already active)
workon nit-env

# Upgrade pip and install all required packages
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 5: Configure Environment Variables (.env)
```bash
cp .env.example .env
nano .env
```

Set:
```ini
SECRET_KEY="your-production-secret-key-here"
DEBUG=False
ALLOWED_HOSTS="localhost,127.0.0.1,nit.pythonanywhere.com,nabil371.pythonanywhere.com"
CSRF_TRUSTED_ORIGINS="https://nit.pythonanywhere.com,https://nabil371.pythonanywhere.com"
SITE_URL="https://nit.pythonanywhere.com"
```
*(Press `Ctrl + O` then `Enter` to save, and `Ctrl + X` to exit nano)*

---

## Step 6: Run Migrations and Collect Static Files
In the same virtualenv (`workon nit-env`):
```bash
# Apply database migrations
python manage.py migrate

# Collect static assets into staticfiles/
python manage.py collectstatic --noinput

# (Optional) Create your admin superuser
python manage.py createsuperuser
```

---

## Step 7: Configure the PythonAnywhere "Web" Tab
Navigate to the **Web** tab on the PythonAnywhere dashboard:

### 1. Code Directories
- **Source code**: `/home/<YOUR_USERNAME>/NIT-Home-website---Django`
- **Working directory**: `/home/<YOUR_USERNAME>/NIT-Home-website---Django`
*(Replace `<YOUR_USERNAME>` with `nit` or `Nabil371` depending on your account)*

### 2. Virtualenv
- Enter the virtualenv path:
  `/home/<YOUR_USERNAME>/.virtualenvs/nit-env`

### 3. WSGI Configuration File
Click on the link for the **WSGI configuration file** (e.g. `/var/www/<YOUR_DOMAIN>_wsgi.py`).
Replace its entire content with:
```python
import os
import sys

# Auto-detect project directory path for 'nit' or 'Nabil371'
possible_paths = [
    '/home/nit/NIT-Home-website---Django',
    '/home/Nabil371/NIT-Home-website---Django',
]

for p in possible_paths:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)
        break
else:
    username = os.environ.get('USER', 'nit')
    custom_path = f'/home/{username}/NIT-Home-website---Django'
    if custom_path not in sys.path:
        sys.path.insert(0, custom_path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'nit_home.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
Click **Save** in the top right corner.

### 4. Static Files Mappings
Under the **Static files** section, add these two entries:

| URL | Directory |
| :--- | :--- |
| `/static/` | `/home/<YOUR_USERNAME>/NIT-Home-website---Django/staticfiles` |
| `/media/` | `/home/<YOUR_USERNAME>/NIT-Home-website---Django/media` |

### 5. Security (HTTPS)
- Toggle **Force HTTPS** to **Enabled**.

---

## Step 8: Reload the Web App
Scroll to the top of the **Web** tab and click the big green **Reload** button.

Your website is now live! 🚀
