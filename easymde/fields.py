from django.db.models import TextField
from django.contrib.admin import widgets as admin_widgets
from .widgets import EasyMDEEditor


class EasyMDEField(TextField):
    def __init__(self, *args, **kwargs):
        options = kwargs.pop('easymde_options', {})
        self.widget = EasyMDEEditor(easymde_options=options)
        super(EasyMDEField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'widget': self.widget}
        defaults.update(kwargs)

        if defaults['widget'] == admin_widgets.AdminTextareaWidget:
            defaults['widget'] = self.widget
        return super(EasyMDEField, self).formfield(**defaults)
