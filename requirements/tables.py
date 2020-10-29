import markdown2
from django.utils.html import format_html, linebreaks
from django.urls import reverse
from django.utils.safestring import mark_safe
from django_markdown2.templatetags.md2 import force_unicode
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
    def render_actions(_record):
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


def row_style(record):
    #  type: (Item) -> str
    style = ''
    if record.deleted:
        style += 'text-decoration: line-through; '
    if record.pending:
        style += 'background-color: #d7ffd3;'
    elif not record.reviewed:
        style += 'background-color: #fffbd3;'
    elif not record.normative:
        style += 'background-color: #f1f1f1;'
    return style


class ExtendedFields(Column):
    def render(self, value, **kwargs):
        value = kwargs['record'].get(kwargs['bound_column'].name)
        if isinstance(value, list):
            return ', '.join(value)
        else:
            return value


class RequirementsTable(Table):
    uid = Column()
    header = Column()
    text = Column()
    level = Column()
    reviewed = BooleanColumn(verbose_name='R.', orderable=False)
    normative = BooleanColumn(verbose_name='N.', orderable=False)
    actions = Column(empty_values=())

    class Meta:
        template_name = "django_tables2/bootstrap4.html"
        row_attrs = {
            "data-heading": lambda record: record.heading,
            "style": lambda record: row_style(record)

        }
        order_by = 'level'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def all_comments_closed(record):
        #  type: (Item) -> bool
        comments = record.get('comments')
        if comments is None:
            return True
        for comment in comments:
            if 'closed' not in comment or not comment['closed']:
                return False
        else:
            return True


    @staticmethod
    def render_uid(value, record):
        # type: (str, Item) -> str
        if record.deleted:
            return record.uid
        else:
            return format_html('<a id="{}" href="{}">{}</a>', record.uid, reverse('item-details', args=[record.document.prefix,
                                                                                                        record.uid.value]), value)

    @staticmethod
    def render_text(    value, record):
        # type: (str, Item) -> str
        return mark_safe(markdown2.markdown(force_unicode(value), safe_mode=True))
        # return mark_safe(linebreaks(record.text))

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
            html += format_html(
                '<a href="{}" class="btn btn-outline-primary btn-sm" title="Restore item"><i class="fa fa-arrow-circle-o-up"></i></a>',
                reverse('item-action', args=[record.document.prefix, record.uid.value, 'restore']))
        html += format_html('<a href="{}" class="btn btn-outline-primary btn-sm" title="Delete item"><i class="fa fa-trash"></i></a>',
                            reverse('item-action', args=[record.document.prefix, record.uid.value, 'delete']))
        html += format_html('</div></div>')

        html += format_html('<div class="btn-toolbar" style="margin-top: 4px;"><div class="btn-group">')
        if not record.reviewed:
            html += format_html('<a href="{}" class="btn btn-outline-danger btn-sm" title="Review item"><i class="fa fa-search"></i></a>',
                                reverse('item-action-return', args=[record.document.prefix, record.uid.value, 'review', 'doc']))
        if not record.cleared:
            html += format_html('<a href="{}" class="btn btn-outline-danger btn-sm" title="Clear links"><i class="fa fa-angellist"></i></a>',
                                reverse('item-action-return', args=[record.document.prefix, record.uid.value, 'clear', 'doc']))

        if not RequirementsTable.all_comments_closed(record):
            html += format_html('<a href="{}" class="btn btn-outline-warning btn-sm" title="There are open comments"><i class="fa fa-comments"></i></a>',
                                reverse('item-details', args=[record.document.prefix, record.uid.value]))

        html += format_html('</div></div>')

        return html
