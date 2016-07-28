
from flask import abort

import http

from app import models


class user_authorization:
    """
    A class that may be used as a `with` block to wrap code that must be
    executed in the context of an appropriately authorized user.
    """

    # Authorization is implemented as a `with` block, rather than as a
    # decorator (like authentication), because we may not be able to determine
    # only from the functions parameters what the objects are that are being
    # manipulated.
    #
    # While our authorization is at present extremely course-grained (users are
    # either authorized or not; thus amenable to being implemented as a
    # decorator), this may change in future; for example, we may want to
    # restrict access to particular projects (and all associated resources) to
    # certain users.

    def __init__ (self, auth_token):
        assert auth_token is not None
        assert auth_token['uid'] is not None
        assert auth_token['authenticator'] is not None
        self.auth_token = auth_token

    def __enter__(self):
        uaz = models.get_user_authorization(
            self.auth_token['uid'],
            self.auth_token['authenticator'],
            abort_not_found=False)
        if uaz is None:
            abort(http.HTTP_403_FORBIDDEN)
        else:
            return uaz

    def __exit__(self, type, value, traceback):
        pass
