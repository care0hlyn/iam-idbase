from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from idbase.util import localized_datetime_string_now, datetime_diff_seconds
from idbase.models import LoginUrlRemoteUser
import logging

logger = logging.getLogger(__name__)


class LoginUrlMiddleware(object):
    """
    Middleware to check the REMOTE_USER variable only when on LOGIN_URL,
    storing the user in the session. This should negate the need for
    AuthenticationMiddleware, RemoteUserMiddleware, and the associated
    AUTHENTICATION_BACKENDS.

    In this scenario, we have a login page that is protected by SSO,
    and multiple other SSO-protected pages that check federation status.
    Authenticate only the REMOTE_USER variable when on the configured
    LOGIN_URL.
    """
    def process_request(self, request):
        """
        Create a new login if on LOGIN_URL. Otherwise use an existing user if
        stored in the session.
        """
        if request.path == settings.LOGIN_URL:
            remote_user = request.META.get('REMOTE_USER', '')
            logger.info('authenticating ' + remote_user)
            request.session.flush()
            request.session['_login_url_remote_user'] = dict(
                remote_user=remote_user)

        request.user = LoginUrlRemoteUser(
            **request.session.get('_login_url_remote_user', {}))


class SessionTimeoutMiddleware(object):
    """
    Middleware to supplement built-in session expiration with an
    independently-managed timeout. This allows us to set
    SESSION_EXPIRE_AT_BROWSER_CLOSE to True while also having an expiration,
    something the default session management doesn't allow for. Allows for
    setting SESSION_TIMEOUT_DEFAULT_SECONDS, the absence of which will set a
    timeout of 20 minutes.
    """
    def __init__(self):
        if not settings.SESSION_EXPIRE_AT_BROWSER_CLOSE:
            raise ImproperlyConfigured(
                'SessionTimeoutMiddleware expects '
                'SESSION_EXPIRE_AT_BROWSER_CLOSE to be True.')

    def process_request(self, request):
        """
        Invalidate a session if expiration is beyond the last session update.
        """
        last_update = request.session.get('_session_timeout_last_update',
                                          localized_datetime_string_now())

        expiry = getattr(settings, 'SESSION_TIMEOUT_DEFAULT_SECONDS', 20*60)

        diff = datetime_diff_seconds(last_update)
        if diff > expiry:
            logger.info(
                'Clearing session on inactivity (diff={}, expiry={}'.format(
                    diff, expiry))
            request.session.flush()

    def process_response(self, request, response):
        """
        Reset the timeout if the session has been modified.
        """
        if request.session.modified:
            request.session['_session_timeout_last_update'] = \
                localized_datetime_string_now()
        return response
