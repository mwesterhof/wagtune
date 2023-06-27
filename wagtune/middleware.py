import random


class VisitorKeyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        visitorKey = request.session.get('visitorKey', 0)
        if not visitorKey:
            visitorKey = random.randint(0, 1024)
            request.session['visitorKey'] = visitorKey

        response = self.get_response(request)
        return response
