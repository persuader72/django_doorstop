from django.utils.html import format_html, linebreaks
from django.urls import reverse
from django.utils.safestring import mark_safe
from django_tables2 import Table, Column, BooleanColumn, CheckBoxColumn

from doorstop import Item

from pygit2 import GIT_STATUS_WT_MODIFIED


class GitFileStatusRecord(object):
    def __init__(self, name, status):
        self.selected = False
        self.name = name
        self.status = status

    def status_text(self):
        if self.status == GIT_STATUS_WT_MODIFIED:
            return 'Modified'


class GitFileStatus(Table):
    selected = CheckBoxColumn()
    name = Column(verbose_name='File name')
    status_text = Column(verbose_name='Status')
    actions = Column(empty_values=())

    class Meta:
        template_name = "django_tables2/bootstrap4.html"

    def __init__(self, data=None):
        super().__init__(data, attrs={'class': 'table table-sm'})

    @staticmethod
    def render_actions(record):
        # type: (Item) -> str
        html = format_html('<div class="btn-toolbar"><div class="btn-group">')
        html += format_html('<a href="{}" class="btn btn-outline-primary btn-sm" title="Unlink parent req"><i class="fa fa-edit"></i></a>',
                            reverse('index', args=[]))
        html += format_html('</div></div>')
        return html


class ParentRequirementTable(Table):
    document = Column(verbose_name='Doc.')
    uid = Column(verbose_name='Parent req')
    actions = Column(empty_values=())

    class Meta:
        template_name = "django_tables2/bootstrap4.html"

    def __init__(self, data=None, item=None):
        self._item = item
        super().__init__(data, attrs={'class': 'table table-sm'})

    # noinspection PyUnusedLocal
    @staticmethod
    def render_uid(value, record):
        # type: (str, Item) -> str
        return format_html('<a id="{}" href="{}">{}</a>', record.uid, reverse('item-details', args=[record.document.prefix, record.uid.value]), value)

    def render_actions(self, record):
        # type: (Item) -> str
        html = format_html('<div class="btn-toolbar"><div class="btn-group">')
        html += format_html('<a href="{}" class="btn btn-outline-primary btn-sm" title="Unlink parent req"><i class="fa fa-unlink"></i></a>',
                            reverse('item-action-target', args=[self._item.document.prefix, self._item.uid.value, 'unlink', record.uid]))
        html += format_html('</div></div>')
        return html


class RequirementsTable(Table):
    uid = Column()
    header = Column()
    text = Column()
    level = Column()
    # active = BooleanColumn(verbose_name='A.', orderable=False)
    reviewed = BooleanColumn(verbose_name='R.', orderable=False)
    normative = BooleanColumn(verbose_name='N.', orderable=False)
    actions = Column(empty_values=())

    class Meta:
        template_name = "django_tables2/bootstrap4.html"
        row_attrs = {
            "data-heading": lambda record: record.heading,
            "style": lambda record: "" if not record.deleted else "text-decoration: line-through"

        }
        order_by = 'level'

    def __init__(self, **kwargs):
        super().__init__(**kwargs, extra_columns=[])

    # noinspection PyUnusedLocal
    @staticmethod
    def render_uid(value, record):
        # type: (str, Item) -> str
        if record.deleted:
            return record.uid
        else:
            return format_html('<a id="{}" href="{}">{}</a>', record.uid, reverse('item-details', args=[record.document.prefix, record.uid.value]), value)

    # noinspection PyUnusedLocal
    @staticmethod
    def render_text(value, record):
        # type: (str, Item) -> str
        return mark_safe(linebreaks(record.text))

    # noinspection PyUnusedLocal
    @staticmethod
    def render_moc(value, record):
        # type: (str, Item) -> str
        return record.moc_label_list(sep=' ')

    # noinspection PyUnusedLocal
    @staticmethod
    def render_system(value, record):
        # type: (str, Item) -> str
        return record.system_list(sep=' ')

    @staticmethod
    def render_actions(record):
        # type: (Item) -> str
        html = format_html('<div class="btn-toolbar"><div class="btn-group">')
        if not record.deleted:
            html += format_html('<a href="{}" class="btn btn-outline-primary btn-sm" title="Edit item"><i class="fa fa-edit"></i></a>',
                                reverse('item-update', args=[record.document.prefix, record.uid.value]))
            html += format_html('<a href="{}" class="btn btn-outline-primary btn-sm" title="View item"><i class="fa fa-eye"></i></a>',
                                reverse('item-details', args=[record.document.prefix, record.uid.value]))
        else:
            html += format_html('<a href="{}" class="btn btn-outline-primary btn-sm" title="Restore item"><i class="fa fa-arrow-circle-o-up"></i></a>',
                                reverse('item-action', args=[record.document.prefix, record.uid.value, 'restore']))
        html += format_html('<a href="{}" class="btn btn-outline-primary btn-sm" title="Delete item"><i class="fa fa-trash"></i></a>',
                            reverse('item-action', args=[record.document.prefix, record.uid.value, 'delete']))
        html += format_html('</div></div>')
        return html
