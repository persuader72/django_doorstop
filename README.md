# django_doorstop

Django_doorstop is a simple web interface for doorstop python library for 
requirement managment.

Use this customized version  of [DoorStop](https://github.com/persuader72/doorstop)
to enable the forgein fileds in requirements.

Install django app

```bash
git clone git@github.com:persuader72/django_doorstop.git
cd django_doorstop
virtualenv venv
source venv/bin/activate
pip install -r requrements.txt
pip install git+https://github.com/persuader72/doorstop.git
```

Configure django app

```bash
cd django_doorstop
cp settings_example.py settings.py
nano settings.py # Change ettings as you prefer
cd ..
```

Run server

```bash
python manage.py 8000
```
