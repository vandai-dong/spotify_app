from django import template
from django.templatetags.static import static

register = template.Library()


def _label(obj):
    return getattr(obj, 'track_name', None) or getattr(obj, 'artist', None) or getattr(obj, 'name', '') or ''


@register.inclusion_tag('partials/_cover.html')
def cover(obj, shape='square', size=None, css='', alt=None):
    """Render an Artist / Song / Album image with a placeholder fallback.

    shape: 'square' (rounded corners), 'circle' or 'sleeve' (album-sleeve look). size: pixel edge; omit to let CSS size it.
    alt: defaults to the object's name; pass '' when the name is printed right next to it.
    """
    classes = ['rounded-circle' if shape == 'circle' else 'sleeve' if shape == 'sleeve' else 'rounded']
    if css:
        classes.append(css)
    return {
        'src': (obj.cover_url if obj is not None else '') or static('img/placeholder.svg'),
        'placeholder': static('img/placeholder.svg'),
        'alt': _label(obj) if alt is None else alt,
        'classes': ' '.join(classes),
        'size': size,
    }
