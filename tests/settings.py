DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.sqlite3'
    }
}

INSTALLED_APPS = [
    'wagtune',
]

SECRET_KEY = 'your_secret_key_for_testing'
