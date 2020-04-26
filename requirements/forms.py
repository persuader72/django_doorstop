import datetime
from typing import Optional, List

import yaml
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

from django import forms
from django.http import QueryDict

from django_ace import AceWidget

from doorstop import Document
from doorstop.core import Item
from doorstop.common import load_yaml


class ItemCommentForm(forms.Form):
    date = forms.DateTimeField(required=True, input_formats=['%Y-%m-%d %H:%M'])
    author = forms.CharField(max_length=255, required=True)
    message = forms.CharField(required=True)

    def __init__(self):
        initial = {
            'date': datetime.datetime.now(),
            'author': 's.pagnottelli'
        }
        super().__init__(initial=initial)
        self.helper = FormHelper(self)
        # self.helper.form_class = 'form-inline'
        self.helper.field_template = 'bootstrap4/layout/inline_field.html'
        self.helper.layout = Layout(
            Row(
                Column("date", css_class='col-md-2'),
                Column("author", css_class='col-md-3'),
                Column("message", css_class='col-md-6'),
                Submit("Add comment", 'submit', css_class='col-md-1'),
                css_class=''
            ),
        )


class DocumentUpdateForm(forms.Form):
    prefix = forms.CharField(max_length=255, required=False, disabled=True)
    sep = forms.CharField(max_length=255, required=False)
    digits = forms.IntegerField(min_value=1, max_value=9)
    yaml = forms.CharField(required=False, widget=forms.Textarea(attrs={'style': 'font-family: monospace;'}))

    def __init__(self, doc=None, post=None):
        # type: (Optional[Document], QueryDict) -> None
        self._doc = doc  # type: Optional[Document]
        initial_data = None
        if doc:
            initial_data = {'prefix': doc.prefix, 'sep': doc.sep, 'digits': doc.digits, 'yaml': ''}
            with open(doc.config, 'r') as stream:
                yaml_data = load_yaml(stream, doc.config)
                if 'attributes' in yaml_data:
                    initial_data['yaml'] = yaml.dump(yaml_data['attributes'])

        if post is not None:
            initial_data['sep'] = post['sep']
            initial_data['digits'] = post['digits']
            initial_data['yaml'] = post['yaml']

        super().__init__(data=initial_data, initial=initial_data)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Row(
                Column('prefix', css_class='form-group col-md-4 mb-0'),
                Column('sep', css_class='form-group col-md-4 mb-0'),
                Column('digits', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            'yaml',
            Submit('submit', 'Submit')
        )

    def save(self):
        self._doc.sep = self.cleaned_data['sep']
        self._doc.digits = self.cleaned_data['digits']
        self._doc.save()
        with open(self._doc.config, 'r') as stream:
            yaml_data = load_yaml(stream, self._doc.config)
            yaml_data_new = yaml.safe_load(self.cleaned_data['yaml'])
            yaml_data['attributes'] = yaml_data_new
            text = self._doc._dump(yaml_data)
            self._doc._write(text, self._doc.config)


class ItemRawEditForm(forms.Form):
    yaml = forms.CharField(widget=AceWidget(mode='yaml', width='100%', height='640px', theme='github', toolbar=False, fontsize='24px'))

    def __init__(self, data=None, item=None):
        self._item = item  # type: Optional[Item]
        initial = {'yaml': item._read(item.path) }
        super().__init__(data=data, initial=initial)
        self.helper = FormHelper(self)
        self.helper.add_input(Submit('submit', "Update file", css_class='btn-primary'))

    def save(self):
        self._item._write(self.cleaned_data['yaml'], self._item.path)


class ItemUpdateForm(forms.Form):
    uid = forms.CharField(max_length=255, required=False, disabled=True)
    level = forms.CharField(max_length=255, required=False)
    header = forms.CharField(max_length=255, required=False)
    text = forms.CharField(widget=forms.Textarea())
    active = forms.BooleanField(required=False)
    normative = forms.BooleanField(required=False)

    def init_forgein_flat_array(self, name, field):
        sep = field['sep'] if 'sep' in field else ';'
        self.fields[name] = forms.CharField(initial=sep.join(self._item.get(name)), required=False)
        self._forgein_fields.append((field['type'], name))

    def init_forgein_multi_choice(self, name, field):
        vv = []
        if 'choices' in field:
            for k in field['choices']:
                vv.append((k, field['choices'][k],))
        self.fields[name] = forms.MultipleChoiceField(choices=tuple(sorted(vv)), initial=self._item.get(name), required=False)
        self._forgein_fields.append((field['type'], name))

    def init_forgein_fields(self):
        ff = self._item.document.forgein_fields
        if not ff:
            return tuple([])

        for ff_name in ff:
            ff_item = ff[ff_name]
            if ff_item['type'] == 'multi':
                self.init_forgein_multi_choice(ff_name, ff_item)
            elif ff_item['type'] == 'flat':
                self.init_forgein_flat_array(ff_name, ff_item)

        vv = []
        if len(self._forgein_fields) > 0:
            for ff_type, ff_name in self._forgein_fields:
                vv.append(Column(ff_name, css_class='form-group col-md-6 mb-0'))

        return tuple(vv)

    def __init__(self, data=None, item=None):
        # type: (Optional[QueryDict], Optional[Item]) -> None
        self._item = item  # type: Optional[Item]
        self._forgein_fields = []  # type: List[tuple]

        initial_data = None
        if item is not None and data is None:
            initial_data = {'uid': item.uid, 'level': item.level, 'header': item.header, 'text': item.text, 'normative': item.normative}

        super().__init__(data=data, initial=initial_data)
        layout = self.init_forgein_fields()

        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Row(
                Column('uid', css_class='form-group col-md-3 mb-0'),
                Column('header', css_class='form-group col-md-4 mb-0'),
                Column('level', css_class='form-group col-md-3 mb-0'),
                Column('normative', css_class='form-group col-md-2 mb-0'),
                css_class='form-row'
            ),
            'text',
            Row(*layout, css_class='form-row'),
            Submit('submit', 'Submit')
        )

    def save(self):
        self._item.level = self.cleaned_data['level']
        self._item.header = self.cleaned_data['header']
        self._item.text = self.cleaned_data['text']
        self._item.normative = self.cleaned_data['normative']

        for _type, name in self._forgein_fields:
            if _type == 'multi':
                self._item.set(name, self.cleaned_data[name])
            elif _type == 'flat':
                self._item.set(name, self.cleaned_data[name].split(','))

        self._item.save()


class RequirementFilterForm(forms.Form):
    MOC_CHOICES = (
        ("", "",),
        ("T", "Reviewed",),
        ("F", "Not reviewed",),
    )

    filter_text = forms.CharField(widget=forms.TextInput,  label='Header or text', required=False)
    filter_review = forms.ChoiceField(choices=MOC_CHOICES, required=False)

    helper = FormHelper()
    helper.form_class = 'form-inline'
    helper.field_template = 'bootstrap4/layout/inline_field.html'
    helper.add_input(Submit('submit', 'Filter', css_class='btn-primary'))
    helper.form_method = 'GET'

