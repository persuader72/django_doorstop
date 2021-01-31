import os
import shutil
import time
from typing import Optional, List, Any

import yaml
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.files.base import File
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpResponseRedirect, FileResponse
from django.urls import reverse, resolve
from django.views.generic import ListView, TemplateView, DetailView
from django.conf import settings
from django_downloadview import VirtualDownloadView, PathDownloadView
from django_tables2 import SingleTableMixin

from jsonview.views import JsonView
from doorstop.core.item import UnknownItem
from doorstop.core.validators.item_validator import ItemValidator
from doorstop.core.types import UID
from doorstop import Tree, Item, DoorstopError, DoorstopInfo, DoorstopWarning
from doorstop.core import Document
from doorstop.core.builder import build

from requirements.djdoorstop import DjItem
from requirements.export import export_full_xslx, import_from_xslx
from requirements.forms import ItemUpdateForm, DocumentUpdateForm, ItemCommentForm, ItemRawEditForm, VirtualItem, DocumentSourceForm
from requirements.tables import RequirementsTable, ParentRequirementTable, GitFileStatus, ExtendedFields, \
    TrashcanRequirementsTable, TrashcanItem
from requirements.repo import MyPyGit2
from requirements.utils import repository_path


class RequirementMixin(LoginRequiredMixin):
    def __init__(self):
        self._user = None  # type: Optional[User]
        self._tree = build(root=settings.DOORSTOP_REPO)  # type: Tree
        self._doc = None  # type: Optional[Document]
        self._item = None  # type: Optional[DjItem]
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

    def check_warnings(self):
        fname = os.path.join(repository_path(self._user), '.django_doorstop')
        if not os.path.exists(fname) or os.path.getmtime(fname) < time.time() - 86400:
            vcsurl = reverse('vcs-show')
            warntxt = f'Your repository is old than 20 hours. Plese pull from server on <a href="{vcsurl}">version control<a> section.'
            return {'type': 'danger', 'text': warntxt}
        else:
            return None


class FileDownloadView(RequirementMixin, DetailView):
    def get(self, request, *args, **kwargs):
        current_url = resolve(request.path_info).url_name
        if current_url == 'doc-media2' or current_url == 'item-update-media2':
            relpath = 'media2'
        else:
            relpath = 'media'
        print(current_url)
        self._doc = self._tree.find_document(kwargs['doc'])
        filename = kwargs['file']
        if filename is None:
            raise ValueError("No filename is provided")
        filename = f'{self._doc.path}/{relpath}/{filename}'
        response = FileResponse(open(filename, 'rb'), content_type="image/png")
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response


class VersionControlView(TemplateView):
    template_name = 'requirements/version_control.html'

    def __init__(self, **kwargs):
        self._curr_file = None
        self._action = None
        self._user = None
        self._curr_file = None  # type: Optional[str]
        self._vcs = None  # type: Optional[MyPyGit2]
        super().__init__(**kwargs)

    def action(self, action, **kwargs):
        #  type: (str, List[Any]) -> None
        if action == 'pull':
            self._vcs.pull()
            with open(os.path.join(repository_path(self._user), '.django_doorstop'), 'a'):
                os.utime(os.path.join(repository_path(self._user), '.django_doorstop'), None)
        elif action == 'push':
            self._vcs.commit_and_push()

    def get(self, request, *args, **kwargs):
        self._user = request.user
        if 'action' in kwargs:
            self._action = kwargs['action']
        if 'f' in request.GET:
            self._curr_file = request.GET['f']
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self._vcs = MyPyGit2(self._user)
        self.action(self._action)
        if self._curr_file:
            tree = build(root=settings.DOORSTOP_REPO)
            context['item'] = tree.find_item(self._curr_file)
        else:
            context['item'] = None
        context['patch'] = self._vcs.diff_patch()
        context['table'] = GitFileStatus(data=self._vcs.modified_files())
        return context


class DocumentIssesView(RequirementMixin, TemplateView):
    template_name = 'requirements/issues.html'

    def get(self, request, *args, **kwargs):
        self._user = request.user
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['docs'] = self._tree.documents
        issues = []
        index = 1
        for issue in self._tree.get_issues():
            if isinstance(issue, DoorstopInfo):
                cls = 'primary'
            elif isinstance(issue, DoorstopWarning):
                cls = 'warning'
            elif isinstance(issue, DoorstopError):
                cls = 'danger'
            issues.append({'index': index, 'class': cls, 'message': str(issue)})
            index += 1
        context['issues'] = issues
        return context


class IndexView(RequirementMixin, SingleTableMixin, ListView):
    template_name = 'requirements/index.html'
    table_class = RequirementsTable
    paginate_by = settings.DOORSTOP_ITEMS_PAGINATE

    def get(self, request, *args, **kwargs):
        self._user = request.user
        self._doc = self._tree.find_document(kwargs['doc']) if 'doc' in kwargs else self._tree.document
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['docs'] = self._tree.documents
        context['warn'] = self.check_warnings()
        return context

    def get_table_kwargs(self):
        dynamic = []
        for _r in self._doc.extended_reviewed:
            dynamic.append((_r, ExtendedFields(accessor='uid')))
        return {'extra_columns': dynamic}

    def get_queryset(self):
        return sorted(i for i in self._doc._iter() if i.active and (not i.deleted or self._user.has_perm('requirements.internal')))


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
        self._form = ItemCommentForm(user=request.user)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        # self._item = self._doc.find_item(kwargs['item'])
        self._prev, self._item, self._next = self.find_neighbours(self._doc, kwargs['item'])
        self._form = ItemCommentForm(request.POST)
        if self._form.is_valid():
            self._form.save(self._item)
            self._form = ItemCommentForm(user=request.user)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['docs'] = self._tree.documents
        context['child_docs'] = self.find_child_docs(self._tree, self._doc)
        context['item'] = self._item
        context['items'] = [str(x.uid) for x in self._doc.items]
        context['prev'] = self._prev
        context['next'] = self._next
        context['childs'] = self._item.find_child_items()
        context['parents'] = [x for x in self._item.parent_items if not isinstance(x, UnknownItem)]
        if self._item.deleted:
            issues = []
        else:
            validator = ItemValidator()
            issues = validator.get_issues(self._item)
        context['issues'] = [str(x) for x in issues]
        context['comments'] = self._item.get('comments')
        context['form'] = self._form
        return context


class ItemAssetView(RequirementMixin, PathDownloadView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._item = self._doc.find_item(kwargs['item'])
        return super().get(request, *args, **kwargs)

    def get_path(self):
        return os.path.join(self._doc.path, self._item.references[0]['path'])


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
        path = export_full_xslx(self._tree)
        file = open(path, 'rb')
        return File(file, name='exported.xlsx')


class DocumentSourceView(RequirementMixin, TemplateView):
    template_name = 'requirements/document_source.html'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._form = None  # type: Optional[DocumentSourceForm]

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._form = DocumentSourceForm(doc=self._doc)
        context = self.get_context_data()
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._form = DocumentSourceForm(doc=self._doc, post=request.POST)
        return self.form_valid() if self._form.is_valid() else self.form_invalid()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['docs'] = self._tree.documents
        context['form'] = self._form
        return context

    def form_valid(self):
        self._form.save()
        return HttpResponseRedirect(reverse('index-doc', args=[self._doc.prefix]))

    def form_invalid(self):
        return self.render_to_response(self.get_context_data(form=self._form))


class DocumentActionView(RequirementMixin, TemplateView):
    template_name = 'requirements/document_action.html'

    ACTION_NAMES = {'import': 'Import', 'clean': 'Clean', 'reorder': 'Reorder'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._action = ''  # type: str
        self._error = None  # type: Optional[str]
        self._confirm = 0  # type: int

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        self._action = kwargs['action']
        self._confirm = int(request.GET.get('confirm', '0'))

        if self._confirm == 1:
            if self._action == 'clean':
                for _i in self._doc.items:  # type: Item
                    _i.review()
                    _i.clear()
                return HttpResponseRedirect(reverse('index-doc', args=[self._doc.prefix]))
        else:
            if self._action == 'reorder':
                self._doc.index = True
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
                return HttpResponseRedirect(reverse('index-doc', args=[self._doc.prefix]))
            elif self._action == 'reorder':
                with open(self._doc.index, 'w') as f:
                    f.write(request.POST['itemIndex'])
                self._doc.reorder()
                return HttpResponseRedirect(reverse('index-doc', args=[self._doc.prefix]))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['action'] = self._action
        context['error'] = self._error
        context['action_name'] = DocumentActionView.ACTION_NAMES[self._action]
        if self._action == 'reorder':
            context['index'] = ''
            if os.path.exists(self._doc.index):
                with open(self._doc.index, 'r') as f:
                    context['index'] = f.read()
        return context


class DocumentTrashcanView(RequirementMixin, SingleTableMixin, ListView):
    template_name = 'requirements/document_trashcan.html'
    table_class = TrashcanRequirementsTable
    paginate_by = settings.DOORSTOP_ITEMS_PAGINATE

    def get(self, request, *args, **kwargs):
        self._user = request.user
        self._doc = self._tree.find_document(kwargs['doc']) if 'doc' in kwargs else self._tree.document
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['docs'] = self._tree.documents
        context['warn'] = self.check_warnings()
        return context

    def get_queryset(self):
        # return self._doc.items
        items = []
        path = os.path.join(self._doc.path, 'trash')
        if not os.path.exists(path):
            os.mkdir(path)
        for filename in os.listdir(path):
            basename, extens = os.path.splitext(filename)
            tcitem = TrashcanItem(self._doc.prefix, basename)
            with open(os.path.join(path, filename), 'r') as f:
                item = yaml.load(f)
                tcitem.header = item.get('header')
                tcitem.text = item.get('text')
            items.append(tcitem)
        return items


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
        self._prev = None  # type: Optional[Item]
        self._next = None  # type: Optional[Item]

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        if kwargs['item'] != '__NEW__':
            self._prev, self._item, self._next = self.find_neighbours(self._doc, kwargs['item'])
            from_item = None
        else:
            from_item = self._tree.find_item(kwargs['from']) if 'from' in kwargs and len(kwargs['from']) > 0 else None
            self._item = VirtualItem(from_item, self._doc.forgein_fields)
        self._form = ItemUpdateForm(item=self._item, doc=self._doc, from_item=from_item)
        context = self.get_context_data()
        context['from'] = from_item
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        if kwargs['item'] != '__NEW__':
            self._item = self._doc.find_item(kwargs['item'])
        self._form = ItemUpdateForm(data=request.POST, item=self._item, doc=self._doc)
        from_item = request.POST.get('from_item', None)
        if from_item is not None and len(from_item) == 0:
            from_item = None
        return self.form_valid(from_item) if self._form.is_valid() else self.form_invalid()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['docs'] = self._tree.documents
        context['item'] = self._item if self._item else {'uid': '__NEW__'}
        context['prev'] = self._prev
        context['next'] = self._next
        context['form'] = self._form
        context['parents'] = [x for x in self._item.parent_items if not isinstance(x, UnknownItem)] if not isinstance(self._item, VirtualItem) else []
        if len(context['parents']) > 0:
            context['table'] = ParentRequirementTable(data=context['parents'], item=self._item)
        return context

    def form_valid(self, from_item):
        #  type: (Optional[Item]) -> HttpResponseRedirect
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
                    'clear': 'Clear', 'closecomm': 'Close Comment'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._action = ''  # type: str
        self._target = None  # type: Optional[Item]
        self._index = -1  # type: int
        self._error = None  # type: Optional[str]
        self._confirm = 0  # type: int
        self._where = 'item'
        self._user = None
        self._vcs = None  # type: Optional[MyPyGit2]

    def action_delete_item(self):
        self._item.deleted = False
        if not os.path.exists(os.path.join(self._doc.path, 'trash')):
            os.mkdir(os.path.join(self._doc.path, 'trash'))
        dstpath = os.path.join(self._doc.path, 'trash', os.path.basename(self._item.path))
        shutil.copy2(self._item.path, dstpath)
        if self._item.references:
            for ref in self._item.references:
                dstpath = os.path.join(self._doc.path, 'trash', os.path.basename(ref['path']))
                shutil.move(ref['path'], dstpath)
        self._item.delete()

    def action_restore_item(self):
        dstpath = os.path.join(self._doc.path, os.path.basename(self._item.path))
        shutil.copy2(self._item.path, dstpath)
        if self._item.references:
            for ref in self._item.references:
                dstpath = os.path.join(self._doc.path, os.path.basename(ref['path']))
                shutil.move(ref['path'], dstpath)
        self._item.delete()

    def get(self, request, *args, **kwargs):
        self._doc = self._tree.find_document(kwargs['doc'])
        try:
            self._item = self._doc.find_item(kwargs['item'])
        except DoorstopError:
            self._item = Item(self._doc, os.path.join(self._doc.path, 'trash', kwargs['item']+'.yml'))
        self._action = kwargs['action']
        self._user = request.user
        self._vcs = MyPyGit2(self._user)

        if 'where' in kwargs:
            self._where = kwargs['where']
        if 'target' in kwargs and kwargs['target']:
            self._target = self._tree.find_item(kwargs['target'])
        if 'index' in kwargs:
            self._index = kwargs['index']
        self._confirm = int(request.GET.get('confirm', '0'))

        self._vcs.test()

        if not self._confirm:
            if self._action == 'link':
                if 'parentuid' in request.GET:
                    try:
                        self._target = self._tree.find_item(request.GET.get('parentuid'))
                    except DoorstopError as ex:
                        self._error = str(ex)
                        print(self._error)
            elif self._action == 'closecomm':
                comments = self._item.get('comments')
                comments[self._index]['closed'] = True
                self._item.set('comments', comments)
                return HttpResponseRedirect("%s" % (reverse('item-details', args=[self._doc.prefix, self._item.uid])))

        if self._confirm == 1:
            if self._action == 'review':
                self._item.review()
                return self._base_redirect()
            elif self._action == 'delete':
                _prev, _item, _next = self.find_neighbours(self._doc, self._item.uid)
                self.action_delete_item()
                return HttpResponseRedirect("%s#%s" % (reverse('index-doc', args=[self._doc.prefix]), _prev.uid))
            elif self._action == 'restore':
                self.action_restore_item()
                return HttpResponseRedirect("%s#%s" % (reverse('index-doc', args=[self._doc.prefix]), self._item.uid))
            elif self._action == 'unlink':
                self._item.unlink(self._target.uid)
                return self._base_redirect()
            elif self._action == 'link':
                self._tree.link_items(self._item.uid, self._target.uid)
                return self._base_redirect()
            elif self._action == 'clear':
                self._item.clear()
                return self._base_redirect()

        context = self.get_context_data()
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doc'] = self._doc
        context['item'] = self._item
        context['action'] = self._action
        context['target'] = self._target
        context['error'] = self._error
        context['where'] = self._where
        context['action_name'] = ItemActionView.ACTION_NAMES[self._action]
        return context

    def _base_redirect(self):
        if self._where == 'doc':
            return HttpResponseRedirect(reverse('index-doc', args=[self._doc.prefix])+'#'+self._item.uid.string)
        else:
            return HttpResponseRedirect(reverse('item-details', args=[self._doc.prefix, self._item.uid]))


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

