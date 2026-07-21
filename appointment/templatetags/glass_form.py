from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def render_glass_form(form):
    """Render a Django form with minimal HTML suitable for glass UI.
    Currently renders each field using the default widget output wrapped in a div.
    """
    html = ''
    for field in form:
        html += f'<div class="mb-3">{field.label_tag()} {field}</div>'
    return mark_safe(html)
