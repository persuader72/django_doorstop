from django import template

register = template.Library()


@register.filter
def first_line_text(text):
    #  type: (str) -> str
    pos = text.find('\n')
    if pos == -1:
        return text
    else:
        return text[0:pos]
