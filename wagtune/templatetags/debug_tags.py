from django.template import Library


register = Library()


@register.simple_tag(takes_context=True)
def tracepoint(context):
    ctx = context
    import ipdb; ipdb.set_trace() 
    return context
