from django.utils.html import format_html, linebreaks
from django.urls import reverse
from django.utils.safestring import mark_safe
from django_tables2 import Table, Column, BooleanColumn


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
