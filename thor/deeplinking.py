from royalnet.typing import *
import itsdangerous


class DeepLinking:
    """A helper class to pass secure information between Telegram and Flask via Telegram Deep Linking."""
    def __init__(self, secret_key: str, namespace: str = "t"):
        self.serializer = itsdangerous.URLSafeSerializer(secret_key=secret_key, salt=namespace)

    def encode(self, value: Any, max_characters: int = 64) -> str:
        signed = self.serializer.dumps(value)
        signed = signed.replace("_", "__").replace(".", "_")
        if len(signed) > 64:
            raise OverflowError("Signed data exceeded 64 characters, it's not suitable for Telegram :(")
        return signed

    def decode(self, signed: str) -> Any:
        signed = signed.replace("_", ".").replace("..", "_")
        value = self.serializer.loads(signed)
        return value
