from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        import accounts.signals

        # Python 3.14 + Django 4.2 compatibility fix:
        # In Python 3.14, copy(super()) inside Django 4.2's BaseContext.__copy__ returns
        # a super proxy object which fails when setting attributes ('dicts').
        # Patch BaseContext.__copy__ to use object.__new__ for safe attribute copying.
        try:
            from django.template.context import BaseContext

            def _base_context_copy(self):
                duplicate = object.__new__(type(self))
                duplicate.__dict__.update(self.__dict__)
                duplicate.dicts = self.dicts[:]
                return duplicate

            BaseContext.__copy__ = _base_context_copy
        except Exception:
            pass
