"""Compatibility patches for Python 3.14+ and Django.

Fixes Django template context copy issue in Python 3.14:
'super' object has no attribute 'dicts' and no __dict__ for setting new attributes
"""
import copy
import django.template.context as django_context


def patch_django_python314():
    """Patch Django's BaseContext.__copy__ for Python 3.14 compatibility."""
    def _base_context_copy(self):
        duplicate = django_context.BaseContext()
        duplicate.__class__ = self.__class__
        duplicate.__dict__ = copy.copy(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    django_context.BaseContext.__copy__ = _base_context_copy


patch_django_python314()
