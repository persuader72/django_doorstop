from django.core.files.uploadedfile import UploadedFile
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View
from jsonview.views import JsonView


@method_decorator(csrf_exempt, name='dispatch')
class IndexView(JsonView):
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['token'] = get_token(request)
        return context

    def post(self, request, *args, **kwargs):
        file = request.FILES['file']  # type: UploadedFile
        with open(f'/tmp/{file.name}', 'wb') as out:
            out.write(file.read())
        context = self.get_context_data(**kwargs)
        context['token'] = get_token(request)
        return context
