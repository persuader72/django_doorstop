from typing import Optional

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView, TemplateView
from django.conf import settings
from django_tables2 import SingleTableMixin

from doorstop.core.validators.item_validator import ItemValidator
from requirements.forms import ItemUpdateForm, DocumentUpdateForm, ItemCommentForm, ItemRawEditForm
from requirements.tables import RequirementsTable, ParentRequirementTable

from doorstop import Tree, Item, DoorstopError
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
    paginate_by = 200

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc']) if 'doc' in kwargs else self._tree.document
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
        self._fprm = ItemCommentForm()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._item = self._doc.find_item(kwargs['item'])
        self._fprm = ItemCommentForm(request.POST)
        if self._fprm.is_valid():
            self._fprm.save(self._item)
            self._fprm = ItemCommentForm()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['item'] = self._item
        context['childs'] = self._item.find_child_items()
        context['parents'] = self._item.parent_items
        validator = ItemValidator()
        issues = validator.get_issues(self._item)
        context['issues'] = [str(x) for x in issues]
        context['comments'] = self._item.get('comments')
        context['form'] = self._fprm
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
        context['parents'] = self._item.parent_items
        return context

    def form_valid(self):
        self._form.save()
        return HttpResponseRedirect(reverse('index-doc', args=[self._doc.prefix]))

    def form_invalid(self):
        return self.render_to_response(self.get_context_data(form=self._form))


class ItemRawFileView(RequirementMixin, TemplateView):
    template_name = 'requirements/item_rawfile.html'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._form = None  # type: Optional[ItemUpdateForm]

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._item = self._doc.find_item(kwargs['item'])
        self._form = ItemRawEditForm(item=self._item)
        context = self.get_context_data()
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._item = self._doc.find_item(kwargs['item'])
        self._form = ItemRawEditForm(data=request.POST, item=self._item)
        return self.form_valid() if self._form.is_valid() else self.form_invalid()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['item'] = self._item
        context['form'] = self._form
        return context

    def form_valid(self):
        self._form.save()
        return HttpResponseRedirect(reverse('item-details', args=[self._doc.prefix, self._item.uid]))

    def form_invalid(self):
        return self.render_to_response(self.get_context_data(form=self._form))


class ItemUpdateView(RequirementMixin, TemplateView):
    template_name = 'requirements/item_update.html'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._form = None  # type: Optional[ItemUpdateForm]

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        if kwargs['item'] != '__NEW__':
            self._item = self._doc.find_item(kwargs['item'])
        self._form = ItemUpdateForm(item=self._item, doc=self._doc)
        context = self.get_context_data()
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        if kwargs['item'] != '__NEW__':
            self._item = self._doc.find_item(kwargs['item'])
        self._form = ItemUpdateForm(data=request.POST, item=self._item, doc=self._doc)
        return self.form_valid() if self._form.is_valid() else self.form_invalid()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['item'] = self._item if self._item else {'uid': '__NEW__'}
        context['form'] = self._form
        parents = self._item.parent_items
        if parents:
            context['table'] = ParentRequirementTable(data=parents, item=self._item)
        return context

    def form_valid(self):
        item = self._form.save()
        return HttpResponseRedirect(reverse('item-details', args=[self._doc.prefix, item.uid]))

    def form_invalid(self):
        return self.render_to_response(self.get_context_data(form=self._form))


class ItemActionView(RequirementMixin, TemplateView):
    template_name = 'requirements/item_action.html'

    ACTION_REVIEW = 'review'
    ACTION_NAMES = {'review': 'Review', 'disactivate': 'Mark inactive', 'delete': 'Delete',
                    'unlink': 'Unlink', 'link': 'Link'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._action = ''  # type: str
        self._target = None  # type: Optional[Item]
        self._error = None  # type: Optional[str]
        self._confirm = 0  # type: int

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._item = self._doc.find_item(kwargs['item'])
        self._action = kwargs['action']
        if 'target' in kwargs and kwargs['target']:
            self._target = self._tree.find_item(kwargs['target'])
        self._confirm = int(request.GET.get('confirm', '0'))

        if not self._confirm:
            if self._action == 'link':
                if 'parentuid' in request.GET:
                    try:
                        self._target = self._tree.find_item(request.GET.get('parentuid'))
                    except DoorstopError as ex:
                        self._error = str(ex)
                        print(self._error)

        if self._confirm == 1:
            if self._action == 'review':
                self._item.review()
                return HttpResponseRedirect(reverse('item-update', args=[self._doc.prefix, self._item.uid]))
            elif self._action == 'delete':
                self._item.delete()
                return HttpResponseRedirect(reverse('index-doc', args=[self._doc.prefix]))
            elif self._action == 'unlink':
                self._item.unlink(self._target.uid)
                return HttpResponseRedirect(reverse('item-update', args=[self._doc.prefix, self._item.uid]))
            elif self._action == 'link':
                self._tree.link_items(self._item.uid, self._target.uid)
                return HttpResponseRedirect(reverse('item-update', args=[self._doc.prefix, self._item.uid]))

        context = self.get_context_data()
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['item'] = self._item
        context['action'] = self._action
        context['target'] = self._target
        context['error'] = self._error
        context['action_name'] = ItemActionView.ACTION_NAMES[self._action]
        return context