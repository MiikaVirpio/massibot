"""
This file is to load Django and use it in an interactive editor.
This means shift+enter in VSCode + Jupyter extension.
"""

# This is to include parent folder for imports
from path import Path
import sys
sys.path.append(Path.cwd().parent)

import os
import django
# This is to enable running of async for Django in interactive mode
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
# This is needed for Django to be initialized
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
django.setup()

from django.contrib.auth.models import User
from chat.models import Profile

user = User.objects.get(id=1)
profile = Profile.objects.create(user=user)

