# Deploying NIT Store to PythonAnywhere (nabil371.pythonanywhere.com)

This step-by-step guide walks you through deploying your Django e-commerce website to PythonAnywhere under your account: **Nabil371**.

---

## ⚠️ Important Note About Free Accounts
PythonAnywhere free accounts allow **one active web application** at `nabil371.pythonanywhere.com`. Since your portfolio was previously deployed there, configuring this project on your Web tab will route your domain to this NIT Store Django application.

---

## Step 1: Push the Latest Code to GitHub
On your local machine (or via this workspace), commit and push changes:
```bash
git add .
git commit -m "Configure settings and WSGI for PythonAnywhere deployment"
git push origin master
```

---

## Step 2: Open PythonAnywhere Bash Console
1. Log in to [pythonanywhere.com](https://www.pythonanywhere.com).
2. Go to the **Consoles** tab and click **Bash** to open a new terminal.

---

## Step 3: Clone or Update the Project
In the PythonAnywhere Bash console:
```bash
# Navigate to home directory
cd ~

# If you haven't cloned the repo yet:
git clone https://github.com/nabilmushfique460/NIT-Home-website---Django.git

# Enter the project folder:
cd NIT-Home-website---Django

# If already cloned previously, pull the latest changes:
git pull origin master
```

---

## Step 4: Create and Configure Virtual Environment
Run the following in the Bash console:
```bash
# Create a dedicated virtualenv with Python 3.10
mkvirtualenv --python=/usr/bin/python3.10 nit-env

# Activate virtualenv (if not already active)
workon nit-env

# Upgrade pip and install all required packages
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 5: Configure Environment Variables (.env)
Create your production `.env` file from the example:
```bash
cp .env.example .env
nano .env
```
Ensure the following key settings are set:
```ini
SECRET_KEY="your-generated-or-custom-secret-key"
DEBUG=False
ALLOWED_HOSTS="localhost,127.0.0.1,nabil371.pythonanywhere.com"
CSRF_TRUSTED_ORIGINS="https://nabil371.pythonanywhere.com"
SITE_URL="https://nabil371.pythonanywhere.com"
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
- **Source code**: `/home/Nabil371/NIT-Home-website---Django`
- **Working directory**: `/home/Nabil371/NIT-Home-website---Django`

### 2. Virtualenv
- Enter the virtualenv path:
  `/home/Nabil371/.virtualenvs/nit-env`

### 3. WSGI Configuration File
Click on the link for the **WSGI configuration file** (usually `/var/www/nabil371_pythonanywhere_com_wsgi.py`).
Replace its entire content with:
```python
import os
import sys

# Project path
path = '/home/Nabil371/NIT-Home-website---Django'
if path not in sys.path:
    sys.path.insert(0, path)

# Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'nit_home.settings'

# WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
Click **Save** in the top right corner.

### 4. Static Files Mappings
Under the **Static files** section, add these two entries:

| URL | Directory |
| :--- | :--- |
| `/static/` | `/home/Nabil371/NIT-Home-website---Django/staticfiles` |
| `/media/` | `/home/Nabil371/NIT-Home-website---Django/media` |

### 5. Security (HTTPS)
- Toggle **Force HTTPS** to **Enabled**.

---

## Step 8: Reload the Web App
Scroll to the top of the **Web** tab and click the big green **Reload nabil371.pythonanywhere.com** button.

Your website is now live at:
👉 **https://nabil371.pythonanywhere.com**
