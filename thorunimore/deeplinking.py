import itsdangerous
from royalnet.typing import *


class DeepLinking:
    """A helper class to pass secure information between Telegram and Flask via Telegram Deep Linking."""

    def __init__(self, secret_key: str, namespace: str = "t"):
        self.serializer = itsdangerous.URLSafeSerializer(secret_key=secret_key, salt=namespace)

    def encode(self, value: Any) -> str:
        signed = self.serializer.dumps(value)
        signed = signed.replace("_", "_u").replace(".", "_d")
        return signed

    def decode(self, signed: str) -> Any:
        signed = signed.replace("_d", ".").replace("_u", "_")
        value = self.serializer.loads(signed)
        return value
