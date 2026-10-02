"""Explicitly armed regular NFO/NRML execution; paper client remains read-only."""
import json
import math
import re
from urllib.parse import urlencode

from .client import BASE_URL, ALLOWED_ENDPOINTS, KiteClient, KiteError, KiteForbiddenEndpoint, KiteHTTPError


class AmbiguousOrderError(KiteError):
    """A write may have reached the broker. Reconcile; never blindly resubmit."""


class KiteExecutionClient(KiteClient):
    def __init__(self, *args, enabled=False, **kwargs):
        if enabled is not True:
            raise KiteError('Live execution requires explicit activation')
        super().__init__(*args, **kwargs)

    def _call(self, method, path, payload=None, timeout=15.0):
        if (method, path) in ALLOWED_ENDPOINTS:
            try:
                return super()._call(method, path, payload, timeout)
            except Exception:
                raise KiteError('Broker calculation/read failed') from None
        allowed = (method == 'GET' and path in ('/orders', '/trades', '/portfolio/positions')) or (
            method == 'POST' and path == '/orders/regular') or (
            method in ('PUT', 'DELETE') and re.fullmatch(r'/orders/regular/[0-9]+', path))
        if not allowed:
            raise KiteForbiddenEndpoint('Endpoint outside live execution scope')
        headers = dict(self._headers)
        body = None
        if payload is not None:
            body = urlencode(payload).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        try:
            return self._transport(method, BASE_URL + path, headers, body, timeout)
        except KiteHTTPError as error:
            if error.status_code in (400, 401, 403, 404, 422):
                raise KiteError('Broker request explicitly rejected') from None
            if method != 'GET':
                raise AmbiguousOrderError('Broker write uncertain; reconcile order book') from None
            raise KiteError('Broker read failed') from None
        except Exception:
            # HTTP failures are also treated as ambiguous: proxies/OMS can fail
            # after acceptance. No raw broker error or credential is emitted.
            if method != 'GET':
                raise AmbiguousOrderError('Broker write uncertain; reconcile order book') from None
            raise KiteError('Broker read failed') from None

    def _json(self, method, path, payload=None):
        try:
            envelope = json.loads(self._call(method, path, payload))
            if envelope.get('status') != 'success':
                raise KiteError('Broker request rejected')
            return envelope['data']
        except (ValueError, KeyError, TypeError):
            if method in ('POST', 'PUT', 'DELETE') and path.startswith('/orders'):
                raise AmbiguousOrderError('Broker write response invalid; reconcile') from None
            raise KiteError('Broker response invalid') from None

    def refresh_access_token(self, access_token):
        if not isinstance(access_token, str) or not access_token or any(c.isspace() for c in access_token):
            raise KiteError('Invalid access token')
        api_key = self._headers['Authorization'].removeprefix('token ').split(':', 1)[0]
        self._headers['Authorization'] = 'token '+api_key+':'+access_token

    def profile(self):
        return self._json('GET', '/user/profile')

    def orders(self):
        return self._json('GET', '/orders')

    def positions(self):
        return self._json('GET', '/portfolio/positions')['net']

    def trades(self):
        return self._json('GET', '/trades')

    def execution_charges(self, orders):
        data = self._json('POST', '/charges/orders', orders)
        if not isinstance(data, list) or len(data) != len(orders):
            raise KiteError('Executed charges unavailable')
        return sum(float(leg['charges']['total']) for leg in data)

    def cash_available(self):
        data = self._json('GET', '/user/margins/equity')
        available = data['available']
        # Do not fund a premium buy using collateral alone.
        return min(float(data['net']), float(available['cash']), float(available['live_balance']))

    @staticmethod
    def _validate(params, placement):
        permitted = {'quantity', 'price', 'trigger_price', 'order_type', 'validity'}
        if placement:
            permitted |= {'tradingsymbol', 'transaction_type', 'tag'}
        if set(params) - permitted:
            raise KiteError('Unsupported order fields')
        if params.get('order_type') not in ('LIMIT', 'SL'):
            raise KiteError('Only LIMIT and SL are supported')
        quantity = params.get('quantity')
        if type(quantity) is not int or quantity <= 0:
            raise KiteError('Positive integer quantity required')
        price = params.get('price')
        if not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            raise KiteError('Positive finite limit price required')
        if params.get('validity', 'DAY') not in ('DAY', 'IOC'):
            raise KiteError('Unsupported validity')
        if params['order_type'] == 'SL':
            trigger = params.get('trigger_price', 0)
            if not math.isfinite(trigger) or trigger < price or params.get('validity', 'DAY') != 'DAY':
                raise KiteError('Sell SL requires DAY and trigger >= limit')
        if placement and (params.get('transaction_type') not in ('BUY', 'SELL') or
                not re.fullmatch(r'[A-Za-z0-9]{1,20}', params.get('tag', '')) or
                not re.fullmatch(r'[A-Za-z0-9]+', params.get('tradingsymbol', ''))):
            raise KiteError('Invalid order identity')
        if placement and params['order_type'] == 'SL' and params['transaction_type'] != 'SELL':
            raise KiteError('Only protective sell stops supported')

    def place_order(self, params):
        self._validate(params, True)
        data = self._json('POST', '/orders/regular', dict(exchange='NFO', product='NRML', **params))
        order_id = str(data.get('order_id', ''))
        if not order_id.isdigit():
            raise AmbiguousOrderError('No broker order ID; reconcile')
        return order_id

    def modify_order(self, order_id, **params):
        if not str(order_id).isdigit():
            raise KiteForbiddenEndpoint('Invalid order ID')
        self._validate(params, False)
        return self._json('PUT', '/orders/regular/' + str(order_id), params)

    def cancel_order(self, order_id):
        if not str(order_id).isdigit():
            raise KiteForbiddenEndpoint('Invalid order ID')
        return self._json('DELETE', '/orders/regular/' + str(order_id))


class KiteMonitorClient(KiteExecutionClient):
    """Dashboard broker reads; write endpoints remain impossible."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, enabled=True, **kwargs)

    def _call(self, method, path, payload=None, timeout=15.0):
        if method != 'GET':
            raise KiteForbiddenEndpoint('Dashboard has no broker write access')
        return super()._call(method, path, payload, timeout)
