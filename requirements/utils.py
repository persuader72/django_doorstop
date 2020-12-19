import os

from django.conf import settings
from django.contrib.auth.models import User


def repository_path(user):
    #  type: (User) -> str
    return settings.DOORSTOP_REPO
    # return os.path.join(settings.DOORSTOP_REPO, user.get_username())
