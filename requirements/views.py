from typing import Optional

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView, TemplateView
from django.conf import settings
from django_tables2 import SingleTableMixin

from requirements.forms import ItemUpdateForm, DocumentUpdateForm
from requirements.tables import RequirementsTable

from doorstop import Tree, Item
from doorstop.core import Document
from doorstop.core.builder import build


class RequirementMixin(object):
    def __init__(self):
        self._tree = build(root=settings.DOORSTOP_REPO)  # type: Tree
        self._doc = None  # type: Optional[Document]
        self._item = None  # type: Optional[Item]

    @staticmethod
    def get_doc(prefix):
        # type: (str) -> Document
        tree = build(root=settings.DOORSTOP_REPO)
        doc = None
        for _doc in tree.documents:
            if _doc.prefix == prefix:
                doc = _doc
                break
        return doc


class IndexView(RequirementMixin, SingleTableMixin, ListView):
    template_name = 'requirements/index.html'
    table_class = RequirementsTable

    def get(self, request, *args, **kwargs):
        self._doc = self.get_doc(kwargs['doc']) if kwargs.get('doc', None) else self._tree.document  # type: Optional[Document]
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['docs'] = self._tree.documents
        return context

    def get_queryset(self):
        return self._doc.items


class ItemDetailView(RequirementMixin, TemplateView):
    template_name = 'requirements/item_details.html'

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._item = self._doc.find_item(kwargs['item'])
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['item'] = self._item
        return context


class DocumentUpdateView(RequirementMixin, TemplateView):
    template_name = 'requirements/document_update.html'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._form = None  # type: Optional[DocumentUpdateForm]

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._form = DocumentUpdateForm(doc=self._doc)
        context = self.get_context_data()
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._form = DocumentUpdateForm(doc=self._doc, post=request.POST)
        return self.form_valid() if self._form.is_valid() else self.form_invalid()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['form'] = self._form
        return context

    def form_valid(self):
        self._form.save()
        return HttpResponseRedirect(reverse('index-doc', args=[self._doc.prefix]))

    def form_invalid(self):
        return self.render_to_response(self.get_context_data(form=self._form))


class ItemUpdateView(RequirementMixin, TemplateView):
    template_name = 'requirements/item_update.html'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._form = None  # type: Optional[ItemUpdateForm]

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._item = self._doc.find_item(kwargs['item'])
        self._form = ItemUpdateForm(item=self._item)
        context = self.get_context_data()
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._item = self._doc.find_item(kwargs['item'])
        self._form = ItemUpdateForm(item=self._item, post=request.POST)
        return self.form_valid() if self._form.is_valid() else self.form_invalid()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['item'] = self._item
        context['form'] = self._form
        return context

    def form_valid(self):
        self._form.save()
        return HttpResponseRedirect(self._form.next_url)

    def form_invalid(self):
        return self.render_to_response(self.get_context_data(form=self._form))
