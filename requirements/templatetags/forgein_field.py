from django import template
from doorstop import Item

register = template.Library()


@register.filter
def forgein_field(obj, attr):
    #  type: (Item, str) -> str
    value = obj.get(attr)
    print(value)
    if value is None:
        return ''
    elif isinstance(value, str):
        return value
    else:
        return ','.join(obj.get(attr))
