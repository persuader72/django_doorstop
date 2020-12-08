# A markdown editor(with preview) for Django
Use markdown editor https://github.com/Ionaru/easy-markdown-editor in django project, this project is inspired by https://github.com/douglasmiranda/django-wysiwyg-redactor/ 

# Getting started

* add 'easymde' to INSTALLED_APPS.

```python
INSTALLED_APPS = (
    # ...
    'easymde',
    # ...
)
```

# Using in models
```python
from django.db import models
from easymde.fields import EasyMDEField

class Entry(models.Model):
    title = models.CharField(max_length=250, verbose_name=u'Title')
    content = EasyMDEField(verbose_name=u'mardown content')
```

# EasyMDE options
You could set EasyMDE options in settings.py like this:

```python
EASYMDE_OPTIONS = {
    'placeholder': 'haha',
    'status': False,
    'autosave': {
        'enabled': True
    }
}
```

Right now this plugin supports [EasyMDE Configurations](https://github.com/Ionaru/easy-markdown-editor#configuration), but only the static ones(don't support js configurations like ```previewRender```)

***for autosave option, you dont need to set it, this plugin will generate uniqueId with python's uuid.uuid4 automatically***

# Get EasyMDE instance from DOM

After EasyMDE initialized, you could get EasyMDE instance from dom element like this:

```javascript
$('.easymde-box')[0].EasyMDE
```