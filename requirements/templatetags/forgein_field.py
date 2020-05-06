from django import template
from doorstop import Item

register = template.Library()


@register.filter
def forgein_field(obj, attr):
    #  type: (Item, str) -> str
    return ','.join(obj.get(attr))
