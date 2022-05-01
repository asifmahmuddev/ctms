"""Authentication backend for the account model."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class CaseInsensitiveModelBackend(ModelBackend):
    """Authenticates on the username field while ignoring letter case.

    An account registered as `User@Example.com` can therefore sign in as `user@example.com`.
    """

    # Django binds the request positionally before the credentials; this backend has no use for it.
    def authenticate(self, _request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        if username is None:
            username = kwargs.get(user_model.USERNAME_FIELD)
        if username is None or password is None:
            return None

        lookup = {f'{user_model.USERNAME_FIELD}__iexact': username}
        try:
            user = user_model._default_manager.get(**lookup)
        except user_model.DoesNotExist:
            # Hash once anyway so an unknown address takes as long as a wrong password.
            user_model().set_password(password)
            return None
        except user_model.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
