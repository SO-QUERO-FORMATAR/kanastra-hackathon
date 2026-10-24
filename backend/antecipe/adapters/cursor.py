import base64
import hashlib
import hmac
import json
from antecipe.application.errors import AppError


class Cursor:
    def __init__(self, secret):
        self.secret = secret.encode()

    def encode(self, data):
        raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
        signature = hmac.new(self.secret, raw, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(signature + raw).decode().rstrip("=")

    def decode(self, token, binding):
        try:
            raw = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
            signature, payload = raw[:32], raw[32:]
            if not hmac.compare_digest(signature, hmac.new(self.secret, payload, hashlib.sha256).digest()):
                raise ValueError()
            data = json.loads(payload)
            if data["binding"] != binding:
                raise ValueError()
            return data
        except (ValueError, KeyError, TypeError, UnicodeError) as exc:
            raise AppError("CURSOR_INVALIDO", "Cursor inválido ou incompatível com os filtros", 400) from exc
