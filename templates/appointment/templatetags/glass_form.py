from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def render_glass_form(form):
    """Render a Django form with custom glassmorphism styling.
    Each field is wrapped in a div with class 'mb-3' and the input receives
    classes for a glass panel. Adjust the classes as needed to match the site's CSS.
    """
    html = ''
    for field in form:
        # Determine field type for appropriate input class
        input_class = 'glass-input form-control'  # base class for styling
        # Add custom classes for widgets like checkboxes/radios if needed
        if field.field.widget.input_type in ['checkbox', 'radio']:
            input_class = 'glass-input custom-control-input'
        # Build label and input
        html += f"<div class='mb-3'>\n"
        html += f"  <label for='id_{field.name}' class='form-label' style='font-weight:600;font-size:13px;text-transform:uppercase;'>{field.label}</label>\n"
        html += f"  {{% if field.errors %}}<div class='text-danger' style='font-size:12px;margin-top:5px;'>{{{{ field.errors }}}}</div>{{% endif %}}\n"
        html += f"  {{{{ field }}}}\n"
        html += f"</div>\n"
    return mark_safe(html)
