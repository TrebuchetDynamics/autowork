"""Consent-only Pi configuration for Hermes' local Nous subscription proxy.

Only GET /health is inspected: /v1/models and `hermes proxy status` can refresh
upstream credentials. Never read auth stores or operate a proxy/service here.
"""
from dataclasses import dataclass, field
import fcntl
import http.client
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urlsplit

DEFAULT_ENDPOINT = 'http://127.0.0.1:8645/v1'
PLACEHOLDER = 'local-proxy-placeholder'


class SetupError(ValueError):
    """Safe diagnostic: never includes configuration contents or response bodies."""


def service_agent_dir(settings):
    """A service inherits its saved directory, never a model picker's environment."""
    return str(Path(settings.get('PI_CODING_AGENT_DIR') or Path.home() / '.pi/agent').expanduser())


def models_path(agent_dir=None):
    directory = Path(agent_dir or os.environ.get('PI_CODING_AGENT_DIR') or Path.home() / '.pi/agent').expanduser()
    if not directory.is_absolute():
        raise SetupError('Use an absolute PI_CODING_AGENT_DIR so setup and services resolve the same Pi configuration.')
    return directory / 'models.json'


def endpoint_parts(endpoint):
    try:
        if not isinstance(endpoint, str):
            raise ValueError('Endpoint must be text')
        parts = urlsplit(endpoint)
        valid = (parts.scheme == 'http' and parts.hostname in ('127.0.0.1', '::1')
                 and parts.port and not parts.username and not parts.password
                 and parts.path.rstrip('/') == '/v1' and not parts.query and not parts.fragment)
        if valid:
            return parts
    except (ValueError, TypeError):
        pass
    raise SetupError('Use a literal loopback HTTP endpoint with a port and /v1 path; no credentials, query or fragment.')


def probe(endpoint):
    """Bounded, unauthenticated local health read, without redirects or env proxies."""
    parts = endpoint_parts(endpoint)
    connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=2)
    try:
        connection.request('GET', '/health')
        response = connection.getresponse()
        body = response.read(8193)
        health = json.loads(body) if response.status == 200 and len(body) <= 8192 else None
        if not isinstance(health, dict) or health.get('status') != 'ok' or health.get('upstream') != 'Nous Portal':
            return {'state': 'incompatible', 'message': 'Not a supported Nous proxy health response; check Hermes version and selected port.'}
        if health.get('authenticated') is not True:
            return {'state': 'login_required', 'message': 'Nous login missing in the proxy profile; run hermes portal there yourself.'}
        return {'state': 'available', 'message': 'Local proxy reports stored authentication; refresh and inference are NOT tested.'}
    except (OSError, ValueError, http.client.HTTPException):
        return {'state': 'unavailable', 'message': 'Proxy unavailable; install Hermes with proxy support, log in with hermes portal, then start hermes proxy start --provider nous on this loopback port yourself.'}
    finally:
        connection.close()


def _read(path, *, for_write=True):
    if for_write and path.is_symlink():
        raise SetupError('Refusing symlinked models.json; select the owning Pi agent directory explicitly.')
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError:
        raise SetupError('Cannot read Pi models.json; check directory permissions.') from None


def _invalid_constant(_):
    raise SetupError('Non-finite numbers are invalid JSON; repair models.json before setup.')


def _finite_float(text):
    value = float(text)
    if not math.isfinite(value):
        _invalid_constant(text)
    return value


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SetupError('Duplicate keys in models.json; resolve them before setup.')
        result[key] = value
    return result


def _validate_entry(entry):
    """Conservative subset of Pi models.json that cannot override proxy routing.

    Pi gives model-level baseUrl/api precedence over the provider. Do not retain
    those overrides (or executable headers) even if they happen to match today:
    changing the provider endpoint would otherwise leave a hidden route behind.
    Share this guard with consumers so later manual edits cannot bypass setup.
    """
    if (not isinstance(entry, dict) or entry.get('apiKey') != PLACEHOLDER
            or entry.get('api') != 'openai-completions'
            or set(entry) - {'baseUrl', 'api', 'apiKey', 'models'}):
        raise SetupError('Selected provider conflicts with proxy setup; choose a new provider name or reconcile it manually.')
    endpoint_parts(entry.get('baseUrl'))
    models = entry.get('models')
    if not isinstance(models, list) or not models:
        raise SetupError('Selected provider needs a nonempty models list; reconcile it manually.')
    ids = set()
    for model in models:
        if (not isinstance(model, dict) or not isinstance(model.get('id'), str)
                or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._:/+-]*', model['id'])
                or model['id'] in ids):
            raise SetupError('Selected provider has invalid or duplicate model entries; reconcile them manually.')
        ids.add(model['id'])
        if set(model) - {'id', 'name', 'reasoning', 'input', 'contextWindow', 'maxTokens', 'cost'}:
            raise SetupError('Selected provider has unsupported model settings or routing/auth overrides; reconcile them manually before proxy setup.')
        valid = ('name' not in model or isinstance(model['name'], str) and bool(model['name']))
        valid &= 'reasoning' not in model or isinstance(model['reasoning'], bool)
        valid &= ('input' not in model or isinstance(model['input'], list)
                  and bool(model['input']) and all(v in ('text', 'image') for v in model['input']))
        for key in ('contextWindow', 'maxTokens'):
            if key in model:
                valid &= type(model[key]) in (int, float) and 0 < model[key] < float('inf')
        if 'cost' in model:
            cost = model['cost']
            valid &= (isinstance(cost, dict) and set(cost) == {'input', 'output', 'cacheRead', 'cacheWrite'}
                      and all(type(v) in (int, float) and 0 <= v < float('inf') for v in cost.values()))
        if not valid:
            raise SetupError('Selected provider has invalid model metadata; reconcile it manually before proxy setup.')


@dataclass
class Proposal:
    path: Path
    provider: str
    model: str
    endpoint: str
    proxy: dict
    prerequisites: list
    original: bytes | None = field(repr=False)
    updated: dict = field(repr=False)

    def result(self, applied=False):
        return {'path': str(self.path), 'provider': self.provider, 'model': f'{self.provider}/{self.model}',
                'endpoint': self.endpoint, 'proxy': self.proxy, 'prerequisites': self.prerequisites,
                'applied': applied, 'message': (
                    'Pi provider prepared; select this provider/model for primary/fallback separately. No service changed; inference NOT tested.'
                    if applied else 'Proposal only: consent required (--apply) to edit only this Pi provider. No proxy/service will be started.')}

    def text(self):
        result = self.result()
        return (f'Nous Portal setup proposal\nPi config: {self.path}\nProvider/model: {result["model"]}\n'
                f'Endpoint: {self.endpoint}\nAPI: openai-completions; key: non-secret local placeholder\n'
                'Credentials remain in Hermes. This endpoint applies to ALL models of the selected provider.\n'
                'Existing models are retained; conflicting providers are refused.\n'
                + '\n'.join(self.prerequisites + [self.proxy['message'], result['message']]))


def propose(provider, model, endpoint=DEFAULT_ENDPOINT):
    if not isinstance(provider, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]*', provider):
        raise SetupError('Select a provider name using letters, numbers, dots, underscores or hyphens.')
    if not isinstance(model, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._:/+-]*', model):
        raise SetupError('Select an exact model ID from your Portal plan; spaces and commands are not allowed.')
    parts = endpoint_parts(endpoint)
    endpoint = f'http://{parts.netloc}/v1'
    path = models_path()
    original = _read(path)
    try:
        data = json.loads(original, object_pairs_hook=_unique, parse_constant=_invalid_constant,
                          parse_float=_finite_float) if original is not None else {}
    except (ValueError, UnicodeError):
        raise SetupError('Invalid Pi models.json; repair the JSON before setup (contents withheld).') from None
    if not isinstance(data, dict) or not isinstance(data.get('providers', {}), dict):
        raise SetupError('Pi models.json must contain an object with a providers object.')
    providers = data.setdefault('providers', {})
    entry = providers.get(provider)
    if provider in providers:
        _validate_entry(entry)
        models = entry['models']
        entry['baseUrl'] = endpoint
        if not any(m['id'] == model for m in models):
            models.append({'id': model})
    else:
        providers[provider] = {'baseUrl': endpoint, 'api': 'openai-completions', 'apiKey': PLACEHOLDER, 'models': [{'id': model}]}
    try:
        # Validate the complete proposed document before consent or filesystem writes.
        json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (ValueError, UnicodeError):
        raise SetupError('Pi models.json contains unsupported JSON values; repair it before setup (contents withheld).') from None
    prerequisites = []
    if not shutil.which(os.environ.get('AUTOWORK_PI') or os.environ.get('PI_BIN') or 'pi'):
        prerequisites.append('Pi not found; install Pi before using this provider.')
    if not shutil.which('hermes'):
        prerequisites.append('Hermes CLI not found; install Hermes with subscription proxy support on this machine.')
    return Proposal(path, provider, model, endpoint, probe(endpoint), prerequisites, original, data)


def apply(proposal):
    """Apply only after caller consent, refusing changes since the displayed proposal."""
    path = proposal.path
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Serialize our own writers; external editors are detected by byte comparison.
        with (path.parent / '.autowork-models.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if _read(path) != proposal.original:
                raise SetupError('Pi models.json changed since proposal; review a fresh proposal before consenting.')
            if proposal.original is not None and json.loads(proposal.original) == proposal.updated:
                return proposal.result(applied=True)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, prefix='.models-', delete=False) as out:
                temporary = out.name
                json.dump(proposal.updated, out, indent=2, ensure_ascii=False, allow_nan=False)
                out.write('\n')
                out.flush()
                os.fsync(out.fileno())
            if _read(path) != proposal.original:
                raise SetupError('Pi models.json changed during setup; no configuration replaced. Review a fresh proposal.')
            os.replace(temporary, path)
            temporary = None
    except OSError:
        raise SetupError('Cannot atomically prepare Pi models.json; check directory permissions. No service changed.') from None
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)
    return proposal.result(applied=True)


def check_model(model, agent_dir=None):
    """Read-only preflight for consumers of entries prepared by this setup."""
    path = models_path(agent_dir)
    original = _read(path, for_write=False)
    if original is None:
        return
    try:
        data = json.loads(original, object_pairs_hook=_unique, parse_constant=_invalid_constant, parse_float=_finite_float)
        entry = data.get('providers', {}).get(model.split('/', 1)[0], {})
    except (ValueError, AttributeError, UnicodeError):
        raise SetupError('Cannot read Pi providers; repair models.json before selecting a model.') from None
    if not isinstance(entry, dict) or entry.get('apiKey') != PLACEHOLDER:
        return
    _validate_entry(entry)
    if model.split('/', 1)[-1] not in {m['id'] for m in entry['models']}:
        raise SetupError('Selected proxy model is not configured; prepare its exact ID with autowork setup-portal --provider NAME --model ID.')
    health = probe(entry['baseUrl'])
    if health['state'] != 'available':
        raise SetupError(health['message'] + ' Inspect setup with autowork setup-portal --provider NAME --model ID.')
