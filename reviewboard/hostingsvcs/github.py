import httplib
import urllib2
from django.utils import simplejson
                                            HostingServiceError,
from reviewboard.scmtools.errors import FileNotFoundError
                                 '%(github_public_repo_name)s/issues#issue/%%s',
    supports_bug_trackers = True
        except Exception, e:
            if str(e) == 'Not Found':
                        _('A repository with this organization or name was not '
                          'found.'))
                body=simplejson.dumps(body))
        except (urllib2.HTTPError, urllib2.URLError), e:
                rsp = simplejson.loads(data)
                raise AuthorizationError(str(e))
        self._save_auth_data(rsp)
    def get_reset_auth_token_requires_password(self):
        """Returns whether or not resetting the auth token requires a password.

        A password will be required if not using a GitHub client ID or
        secret.
        """
        if not self.is_authorized():
            return True

        app_info = self.account.data['authorization']['app']
        client_id = app_info.get('client_id', '')
        has_client = (client_id.strip('0') != '')

        return (not has_client or
                (not (hasattr(settings, 'GITHUB_CLIENT_ID') and
                      hasattr(settings, 'GITHUB_CLIENT_SECRET'))))

    def reset_auth_token(self, password=None, two_factor_auth_code=None):
        """Resets the authorization token for the linked account.

        This will attempt to reset the token in a few different ways,
        depending on how the token was granted.

        Tokens linked to a registered GitHub OAuth app can be reset without
        requiring any additional credentials.

        Tokens linked to a personal account (which is the case on most
        installations) require a password and possibly a two-factor auth
        code. Callers should call get_reset_auth_token_requires_password()
        before determining whether to pass a password, and should pass
        a two-factor auth code if this raises TwoFactorAuthCodeRequiredError.
        """
        if self.is_authorized():
            token = self.account.data['authorization']['token']
        else:
            token = None

        if self.get_reset_auth_token_requires_password():
            assert password

            if self.account.local_site:
                local_site_name = self.account.local_site.name
            else:
                local_site_name = None

            if token:
                try:
                    self._delete_auth_token(
                        self.account.data['authorization']['id'],
                        password=password,
                        two_factor_auth_code=two_factor_auth_code)
                except HostingServiceError, e:
                    # If we get a Not Found, then the authorization was
                    # probably already deleted.
                    if str(e) != 'Not Found':
                        raise

                self.account.data['authorization'] = ''
                self.account.save()

            # This may produce errors, which we want to bubble up.
            self.authorize(self.account.username, password,
                           self.account.hosting_url,
                           two_factor_auth_code=two_factor_auth_code,
                           local_site_name=local_site_name)
        else:
            # We can use the new API for resetting the token without
            # re-authenticating.
            auth_data = self._reset_authorization(
                settings.GITHUB_CLIENT_ID,
                settings.GITHUB_CLIENT_SECRET,
                token)
            self._save_auth_data(auth_data)

        except (urllib2.URLError, urllib2.HTTPError):
        except (urllib2.URLError, urllib2.HTTPError):
    def _reset_authorization(self, client_id, client_secret, token):
        """Resets the authorization info for an OAuth app-linked token.
        If the token is associated with a registered OAuth application,
        its token will be reset, without any authentication details required.
        """
        url = '%sapplications/%s/tokens/%s' % (
            self.get_api_url(self.account.hosting_url),
            client_id,
            token)

        # Allow any errors to bubble up
        return self._api_post(url=url,
                              username=client_id,
                              password=client_secret)

    def _delete_auth_token(self, auth_id, password, two_factor_auth_code=None):
        """Requests that an authorization token be deleted.

        This will delete the authorization token with the given ID. It
        requires a password and, depending on the settings, a two-factor
        authentication code to perform the deletion.
        """
        headers = {}
        if two_factor_auth_code:
            headers['X-GitHub-OTP'] = two_factor_auth_code
        url = self._build_api_url(
            '%sauthorizations/%s' % (
                self.get_api_url(self.account.hosting_url),
                auth_id))
        self._api_delete(url=url,
                         headers=headers,
                         username=self.account.username,
                         password=password)
    def _save_auth_data(self, auth_data):
        """Saves authorization data sent from GitHub."""
        self.account.data['authorization'] = auth_data
        self.account.save()
        elif 'errors' in rsp and status_code == httplib.UNPROCESSABLE_ENTITY:
                                   owner, repo_name)
    def _api_get(self, url, *args, **kwargs):
            data, headers = self._json_get(url, *args, **kwargs)
            return data
        except (urllib2.URLError, urllib2.HTTPError), e:
            self._check_api_error(e)
    def _api_post(self, url, *args, **kwargs):
        try:
            data, headers = self._json_post(url, *args, **kwargs)
            return data
        except (urllib2.URLError, urllib2.HTTPError), e:
            self._check_api_error(e)
    def _api_delete(self, url, *args, **kwargs):
        try:
            data, headers = self._json_delete(url, *args, **kwargs)
            return data
        except (urllib2.URLError, urllib2.HTTPError), e:
            self._check_api_error(e)
    def _check_api_error(self, e):
        data = e.read()
        try:
            rsp = simplejson.loads(data)
        except:
            rsp = None
        if rsp and 'message' in rsp:
            response_info = e.info()
            x_github_otp = response_info.get('X-GitHub-OTP', '')
            if x_github_otp.startswith('required;'):
                raise TwoFactorAuthCodeRequiredError(
                    _('Enter your two-factor authentication code. '
                      'This code will be sent to you by GitHub.'))
            if e.code == 401:
                raise AuthorizationError(rsp['message'])
            raise HostingServiceError(rsp['message'])
        else:
            raise HostingServiceError(str(e))