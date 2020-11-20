from django import template
from doorstop import Item

register = template.Library()


@register.filter
def foreign_field(obj, attr):
    #  type: (Item, str) -> str
    if not obj:
        return ''
    else:
        value = obj.get(attr)
        if value is None:
            return ''
        elif isinstance(value, str):
            return value
        else:
            return ','.join(obj.get(attr))
