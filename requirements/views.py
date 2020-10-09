from typing import Optional, List

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import File
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpResponseRedirect, FileResponse
from django.urls import reverse
from django.views.generic import ListView, TemplateView, DetailView
from django.conf import settings
from django_downloadview import VirtualDownloadView
from django_tables2 import SingleTableMixin
from jsonview.views import JsonView

from doorstop.core.validators.item_validator import ItemValidator

from doorstop.core.types import UID
from requirements.export import export_to_xlsx, import_from_xslx
from requirements.forms import ItemUpdateForm, DocumentUpdateForm, ItemCommentForm, ItemRawEditForm, VirtualItem
from requirements.tables import RequirementsTable, ParentRequirementTable, GitFileStatus, GitFileStatusRecord

from doorstop import Tree, Item, DoorstopError
from doorstop.core import Document
from doorstop.core.builder import build

from pygit2 import init_repository, Repository


class RequirementMixin(LoginRequiredMixin):
    def __init__(self):
        self._tree = build(root=settings.DOORSTOP_REPO)  # type: Tree
        self._doc = None  # type: Optional[Document]
        self._item = None  # type: Optional[Item]
        self._form = None

    @staticmethod
    def find_neighbours(doc, value):
        #  type: (Document, str) -> (Optional[Item], Optional[Item], Optional[Item])
        uid = UID(value)

        found = False
        _prev = None  # type: Optional[Item]
        _item = None  # type: Optional[Item]
        _next = None  # type: Optional[Item]

        for __item in doc.items:
            if not found:
                _prev = _item
                _item = __item
                if __item.uid == uid:
                    found = True
            else:
                if __item.active and not __item.deleted:
                    _next = __item
                    break

        return (_prev, _item, _next) if found else (None, None, None)


    @staticmethod
    def find_child_docs(tree, doc):
        #  type: (Tree, Document) -> List[Document]
        childs = []
        for _d in tree.documents:  # type: Document
            if _d.prefix == doc.prefix:
                continue
            if _d.parent == doc.prefix:
                childs.append(_d)
        return childs

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


class FileDownloadView(RequirementMixin, DetailView):
    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        filename = kwargs['file']
        if filename is None:
            raise ValueError("No filename is provided")
        filename = f'{self._doc.path}/media/{filename}'
        response = FileResponse(open(filename, 'rb'), content_type="image/png")
        response['Content-Disposition'] = 'attachment; filename="%s"'%filename
        return response


class VersionControlView(RequirementMixin, TemplateView):
    template_name = 'requirements/version_control.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        patch_text = ''
        repo = init_repository(settings.DOORSTOP_REPO)
        for patch in repo.diff():
            patch_text += patch.text
        context['patch'] = patch_text

        table_data = []
        status = repo.status()
        for stat in status:
            if status[stat] != GIT_STATUS_IGNORED:
                table_data.append(GitFileStatusRecord(stat, status[stat]))
        context['table'] = GitFileStatus(data=table_data)

        return context


class IndexView(RequirementMixin, SingleTableMixin, ListView):
    template_name = 'requirements/index.html'
    table_class = RequirementsTable
    paginate_by = settings.DOORSTOP_ITEMS_PAGINATE

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc']) if 'doc' in kwargs else self._tree.document
        #repo = init_repository('.')
        #print(repo.diff())
        #for patch in repo.diff():
        #    print(patch.text)
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._prev = None  # type: Optional[Item]
        self._next = None  # type: Optional[Item]

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        # self._item = self._doc.find_item(kwargs['item'])
        self._prev, self._item, self._next = self.find_neighbours(self._doc, kwargs['item'])
        self._form = ItemCommentForm()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        # self._item = self._doc.find_item(kwargs['item'])
        self._prev, self._item, self._next = self.find_neighbours(self._doc, kwargs['item'])
        self._form = ItemCommentForm(request.POST)
        if self._form.is_valid():
            self._form.save(self._item)
            self._form = ItemCommentForm()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['child_docs'] = self.find_child_docs(self._tree, self._doc)
        context['item'] = self._item
        context['prev'] = self._prev
        context['next'] = self._next
        context['childs'] = self._item.find_child_items()
        context['parents'] = self._item.parent_items
        validator = ItemValidator()
        issues = validator.get_issues(self._item)
        context['issues'] = [str(x) for x in issues]
        context['comments'] = self._item.get('comments')
        context['form'] = self._form
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
        context['parents'] = self._item.parent_items if hasattr(self._item, 'parent_items') else []
        return context

    def form_valid(self):
        self._form.save()
        return HttpResponseRedirect(reverse('index-doc', args=[self._doc.prefix]))

    def form_invalid(self):
        return self.render_to_response(self.get_context_data(form=self._form))


class DocumentExportView(RequirementMixin, VirtualDownloadView):
    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        print(self._doc.prefix)
        return super().get(request, *args, **kwargs)

    def get_file(self):
        path = export_to_xlsx(self._doc)
        file = open(path, 'rb')
        return File(file, name='exported.xlsx')


class DocumentActionView(RequirementMixin, TemplateView):
    template_name = 'requirements/document_action.html'

    ACTION_NAMES = {'import': 'Import'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._action = ''  # type: str
        self._error = None  # type: Optional[str]
        self._confirm = 0  # type: int

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._action = kwargs['action']
        self._confirm = int(request.GET.get('confirm', '0'))

        context = self.get_context_data()
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._action = kwargs['action']
        self._confirm = int(request.POST.get('confirm', '0'))

        if self._confirm == 1:
            if self._action == 'import':
                file = request.FILES['file_to_import']  # type: UploadedFile
                with open('/tmp/import.xlsx', 'wb') as f:
                    f.write(file.read())
                import_from_xslx(self._doc)
                print(file.name, file.size, file.content_type)
                return HttpResponseRedirect(reverse('index-doc', args=[self._doc.prefix]))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['action'] = self._action
        context['error'] = self._error
        context['action_name'] = ItemActionView.ACTION_NAMES[self._action]
        return context


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
            from_item = None
        else:
            from_item = self._tree.find_item(kwargs['from']) if 'from' in kwargs else None
            self._item = VirtualItem(from_item, self._doc.forgein_fields)
        self._form = ItemUpdateForm(item=self._item, doc=self._doc)
        context = self.get_context_data()
        context['from'] = from_item
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        if kwargs['item'] != '__NEW__':
            self._item = self._doc.find_item(kwargs['item'])
        self._form = ItemUpdateForm(data=request.POST, item=self._item, doc=self._doc)
        from_item = request.POST.get('from_item', None)
        return self.form_valid(from_item) if self._form.is_valid() else self.form_invalid()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['item'] = self._item if self._item else {'uid': '__NEW__'}
        context['form'] = self._form
        parents = self._item.parent_items if hasattr(self._item, 'parent_items') else []
        if parents:
            context['table'] = ParentRequirementTable(data=parents, item=self._item)
        return context

    def form_valid(self, from_item):
        #  type: (Optional[Item]) -> None
        item = self._form.save()
        if from_item is not None:
            self._tree.link_items(item.uid, from_item)
        return HttpResponseRedirect(reverse('item-details', args=[self._doc.prefix, item.uid]))

    def form_invalid(self):
        return self.render_to_response(self.get_context_data(form=self._form))


class ItemActionView(RequirementMixin, TemplateView):
    template_name = 'requirements/item_action.html'

    ACTION_REVIEW = 'review'
    ACTION_NAMES = {'review': 'Review', 'disactivate': 'Mark inactive', 'delete': 'Delete',
                    'unlink': 'Unlink', 'link': 'Link', 'restore': 'Restore', 'import': 'Import',
                    'clear': 'Clear'}

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
                if self._item.deleted:
                    self._item.delete()
                else:
                    self._item.deleted = True
                return HttpResponseRedirect("%s#%s" % (reverse('index-doc', args=[self._doc.prefix]), self._item.uid))
            elif self._action == 'restore':
                self._item.deleted = False
                return HttpResponseRedirect("%s#%s" % (reverse('index-doc', args=[self._doc.prefix]), self._item.uid))
            elif self._action == 'unlink':
                self._item.unlink(self._target.uid)
                return HttpResponseRedirect(reverse('item-update', args=[self._doc.prefix, self._item.uid]))
            elif self._action == 'link':
                self._tree.link_items(self._item.uid, self._target.uid)
                return HttpResponseRedirect(reverse('item-update', args=[self._doc.prefix, self._item.uid]))
            elif self._action == 'clear':
                self._item.clear()
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


class FullGraphView(RequirementMixin, TemplateView):
    template_name = 'requirements/full_graph.html'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._form = None  # type: Optional[ItemUpdateForm]

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['item'] = self._item if self._item else {'uid': '__NEW__'}
        context['form'] = self._form
        parents = self._item.parent_items if hasattr(self._item, 'parent_items') else []
        if parents:
            context['table'] = ParentRequirementTable(data=parents, item=self._item)
        return context


class GrpahDataView(RequirementMixin, JsonView):
    def _index_of_item(self, look):
        index = 0
        for item in self._doc:
            if item.uid == look.uid:
                return index
            index += 1
        return -1

    def get_context_data(self, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        context = super().get_context_data(**kwargs)

        nodes = []
        nodes.append({"name": "ANDROS", "width": 60, "height": 40, "group": 0})
        for item in self._doc:
            nodes.append({"name": str(item.uid), "width": 60, "height": 40, "group": 1})
        context['nodes'] = nodes

        index = 1
        links = []
        for item in self._doc:
            parents = item.parent_items
            if not parents:
                links.append({'source': 0, 'target': index})
            else:
                for parent in parents:
                    links.append({'source': self._index_of_item(parent), 'target': index})

            index += 1
        context['links'] = links

        return context

