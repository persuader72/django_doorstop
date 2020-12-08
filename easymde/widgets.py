import uuid

from django import forms
from django.conf import settings

from .utils import json_dumps


GLOBAL_OPTIONS = getattr(settings, 'EASYMDE_OPTIONS', {})


class EasyMDEEditor(forms.widgets.Textarea):
    template_name = 'easymde/widgets/easymde.html'

    def __init__(self, *args, **kwargs):
        self.custom_options = kwargs.pop('easymde_options', {})
        super(EasyMDEEditor, self).__init__(*args, **kwargs)

    @property
    def options(self):
        options = GLOBAL_OPTIONS.copy()
        options.pop('custom_init_js', None)
        options.pop('custom_init_css', None)
        if 'autosave' in options and options['autosave'].get('enabled', False):
            options['autosave']['uniqueId'] = str(uuid.uuid4())
        options.update(self.custom_options)
        return options

    @property
    def media(self):
        custom_css = GLOBAL_OPTIONS.get('custom_css', [])
        custom_js = GLOBAL_OPTIONS.get('custom_init_js', ['easymde/easymde.init.js'])
        return forms.Media(
            css={'all': ('easymde/easymde.min.css', *custom_css)},
            js=('easymde/easymde.min.js', *custom_js)
        )

    def get_context(self, name, value, attrs=None):
        if 'class' not in attrs.keys():
            attrs['class'] = ''

        attrs['class'] += ' easymde-box'
        attrs['data-easymde-options'] = json_dumps(self.options)

        context = super().get_context(name, value, attrs)
        context['custom_options'] = self.custom_options
        return context
