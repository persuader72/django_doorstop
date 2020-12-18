import datetime
import os
from typing import Optional, List, Dict

import yaml
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

from django import forms
from django.contrib.auth.models import User
from django.http import QueryDict
from django.urls import reverse

from django_ace import AceWidget

from doorstop import Document
from doorstop.core import Item
from doorstop.common import load_yaml
from easymde.widgets import EasyMDEEditor


class VirtualItem(object):
    def __init__(self, item=None, fields=None):
        self.uid = '__NEW__'
        self.level = ''
        self.header = item.header if item else ''
        self.text = item.text if item else 'Requiremen text...'
        self.normative = item.normative if item else ''
        self.pending = item.pending if item else ''
        self._data = {}

        if fields is not None:
            for f in fields:
                self._data[f] = item.get(f) if item else ''

    def get(self, field):
        return self._data.get(field, None)


class ItemCommentForm(forms.Form):
    date = forms.DateTimeField(required=True, input_formats=['%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'])
    author = forms.CharField(max_length=255, required=True)
    text = forms.CharField(required=True)

    def __init__(self, data=None, user=None):
        #  type: (Optional[Dict], Optional[User]) -> None
        if  user:
            name = user.get_full_name() if len(user.get_full_name()) > 0 else user.get_username()
        else:
            name = 'stefano'
        initial = {
            'date': datetime.datetime.now(),
            'author': name,
            'text': ''
        }
        super().__init__(data=data, initial=initial)
        self.helper = FormHelper(self)
        # self.helper.form_class = 'form-inline'
        self.helper.field_template = 'bootstrap4/layout/inline_field.html'
        self.helper.layout = Layout(
            Row(
                Column("date", css_class='col-md-2'),
                Column("author", css_class='col-md-3'),
                Column("text", css_class='col-md-6'),
                Submit("Add comment", 'submit', css_class='col-md-1'),
                css_class=''
            ),
        )

    def save(self, item):
        # type: (Item) -> None
        comments = item.get('comments', [])
        comments.insert(0, {'date': self.cleaned_data['date'], 'author': self.cleaned_data['author'], 'text': self.cleaned_data['text']})
        item.set('comments', comments)
        item.save()


class DocumentSourceForm(forms.Form):
    metadata = forms.CharField(widget=forms.HiddenInput())
    source = forms.CharField(widget=EasyMDEEditor)

    def __init__(self, doc=None, post=None):
        #  type: (Optional[Document], Optional[Dict]) -> None
        self._doc = doc  # type: Optional[Document]
        self._filepath = os.path.join(doc.path, 'source.md')  # type: str
        initial_data =  {'source': '', 'metadata': ''}

        if post is not None:
            initial_data['source'] = post['source']
            initial_data['metadata'] = post['metadata']
        elif os.path.exists(self._filepath):
            initial_data = DocumentSourceForm.read_source(self._filepath)
        super().__init__(data=initial_data, initial=initial_data)
        self.helper = FormHelper(self)
        self.helper.add_input(Submit('submit', "Update Source", css_class='btn-primary'))

    def save(self):
        _meta = self.cleaned_data['metadata']
        _source = self.cleaned_data['source']

        with open(self._filepath, 'w') as f:
            if len(_meta) > 0:
                f.write(_meta)
                f.write('\n')
            f.write(_source)

    @staticmethod
    def read_source(filename):
        initial_data = {'source': '', 'metadata': ''}

        meta = ''
        source = ''
        state = 0
        with open(filename, 'r') as f:
            for line in f:
                if state == 0:
                    striped = line.strip()
                    if len(striped) > 0:
                        if striped == '---':
                            meta += line
                            state = 1
                        else:
                            state = 2
                            source = line
                elif state == 1:
                    striped = line.strip()
                    if striped == '---':
                        meta += line
                        state = 2
                    else:
                        meta += line
                elif state == 2:
                    striped = line.strip()
                    if len(striped) > 0:
                        source += line
                        state = 3
                else:
                    source += line

        initial_data['metadata'] = meta
        initial_data['source'] = source
        return initial_data


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
    text = forms.CharField(widget=EasyMDEEditor)
    active = forms.BooleanField(required=False)
    normative = forms.BooleanField(required=False)
    pending = forms.BooleanField(required=False)

    def init_foreign_string(self, name, field):
        initial = self._item.get(name) if self._item else ''
        self.fields[name] = forms.CharField(initial=initial, required=False)
        self._foreign_fields.append((field['type'], name))

    def init_foreign_flat_array(self, name, field):
        sep = field['sep'] if 'sep' in field else ';'
        initial = sep.join(self._item.get(name)) if self._item else None
        self.fields[name] = forms.CharField(initial=initial, required=False)
        self._foreign_fields.append((field['type'], name))

    def init_foreign_multi_choice(self, name, field):
        vv = []
        if 'choices' in field:
            for k in field['choices']:
                vv.append((k, field['choices'][k],))
        initial = self._item.get(name) if self._item else None
        self.fields[name] = forms.MultipleChoiceField(choices=tuple(sorted(vv)), initial=initial, required=False)
        self._foreign_fields.append((field['type'], name))

    def init_foreign_single_choice(self, name, field):
        vv = []
        if 'choices' in field:
            for k in field['choices']:
                vv.append((k, field['choices'][k],))
        initial = self._item.get(name) if self._item else None
        self.fields[name] = forms.ChoiceField(choices=tuple(sorted(vv)), initial=initial, required=False)
        self._foreign_fields.append((field['type'], name))

    def init_foreign_fields(self):
        ff = self._doc.forgein_fields
        if not ff:
            return tuple([])

        for ff_name in ff:
            ff_item = ff[ff_name]
            print(ff_name, ff_item['type'])
            if ff_item['type'] == 'multi':
                self.init_foreign_multi_choice(ff_name, ff_item)
            elif ff_item['type'] == 'single':
                self.init_foreign_single_choice(ff_name, ff_item)
            elif ff_item['type'] == 'flat':
                self.init_foreign_flat_array(ff_name, ff_item)
            elif ff_item['type'] == 'string':
                self.init_foreign_string(ff_name, ff_item)
        vv = []
        if len(self._foreign_fields) > 0:
            for ff_type, ff_name in self._foreign_fields:
                vv.append(Column(ff_name, css_class='form-group col-md-6 mb-0'))

        return tuple(vv)

    def __init__(self, data=None, item=None, doc=None):
        # type: (Optional[QueryDict], Optional[Item], Optional[Document]) -> None
        self._item = item  # type: Optional[Item]
        self._doc = doc  # type: Optional[Document]
        if self._doc is None and self._item is not None:
            self._doc = self._item.document
        self._foreign_fields = []  # type: List[tuple]

        initial_data = None
        if item is not None and data is None:
            initial_data = {'uid': item.uid, 'level': item.level, 'header': item.header, 'text': item.text, 'normative': item.normative,
                            'pending': item.pending}

        super().__init__(data=data, initial=initial_data)
        layout = self.init_foreign_fields()

        self.helper = FormHelper(self)
        if item is not None:
            self.helper.form_action = reverse('item-update', args=(self._doc.prefix, self._item.uid))
        self.helper.layout = Layout(
            Row(
                Column('uid', css_class='form-group col-md-3 mb-0'),
                Column('header', css_class='form-group col-md-4 mb-0'),
                Column('level', css_class='form-group col-md-3 mb-0'),
                Column(Row('normative'), Row('pending'), css_class='form-group col-md-2 mb-0'),
                css_class='form-row'
            ),
            'text',
            Row(*layout, css_class='form-row'),
            Submit('submit', 'Submit')
        )

    def save(self):
        #  type: () -> Item
        if not self._item:
            self._item = self._doc.add_item()
            self.helper.form_action = reverse('item-update', args=(self._doc.prefix, self._item.uid))
        if self.cleaned_data['level']:
            self._item.level = self.cleaned_data['level']
        self._item.header = self.cleaned_data['header']
        self._item.text = self.cleaned_data['text']
        self._item.normative = self.cleaned_data['normative']
        self._item.pending = self.cleaned_data['pending']

        for _type, name in self._foreign_fields:
            if _type == 'multi' or _type == 'string' or _type == 'single':
                self._item.set(name, self.cleaned_data[name])
            elif _type == 'flat':
                self._item.set(name, self.cleaned_data[name].split(','))

        self._item.save()
        return self._item


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

