from django.utils.html import format_html, linebreaks
from django.urls import reverse
from django.utils.safestring import mark_safe
from django_tables2 import Table, Column, BooleanColumn

from doorstop import Item


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
        return format_html('<a href="{}">{}</a>', reverse('item-details', args=[record.document.prefix, record.uid.value]), value)

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
    active = BooleanColumn(verbose_name='A.', orderable=False)
    reviewed = BooleanColumn(verbose_name='R.', orderable=False)
    normative = BooleanColumn(verbose_name='N.', orderable=False)
    actions = Column(empty_values=())

    class Meta:
        template_name = "django_tables2/bootstrap4.html"
        row_attrs = {"style": lambda record: "" if record.active else "text-decoration: line-through"}
        order_by = 'level'

    # noinspection PyUnusedLocal
    @staticmethod
    def render_uid(value, record):
        # type: (str, Item) -> str
        return format_html('<a href="{}">{}</a>', reverse('item-details', args=[record.document.prefix, record.uid.value]), value)

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
        html += format_html('<a href="{}" class="btn btn-outline-primary btn-sm" title="Edit item"><i class="fa fa-edit"></i></a>',
                            reverse('item-update', args=[record.document.prefix, record.uid.value]))
        html += format_html('<a href="{}" class="btn btn-outline-primary btn-sm" title="View item"><i class="fa fa-eye"></i></a>',
                            reverse('item-details', args=[record.document.prefix, record.uid.value]))
        html += format_html('<a href="{}" class="btn btn-outline-primary btn-sm" title="Delete item"><i class="fa fa-trash"></i></a>',
                            reverse('item-action', args=[record.document.prefix, record.uid.value, 'delete']))
        html += format_html('</div></div>')
        return html
