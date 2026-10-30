import os
os.environ['DJANGO_SETTINGS_MODULE']='core.settings'
os.environ['DJANGO_LOAD_DOTENV']='false'
os.environ['DJANGO_SECRET_KEY']='test-only-not-for-deployment'
os.environ['OPENAI_API_KEY']=''
import django
django.setup()
import pytest
from django.core.cache import cache

@pytest.fixture(autouse=True)
def clear_throttles():
    cache.clear()
