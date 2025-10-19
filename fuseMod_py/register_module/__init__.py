from ..FuseModManager import FuseModManager
from .simpleModule import SimpleModule
from .emailModule import EmailModule
from .cloudflareKVModule import CloudFlareKVModule

def register_modules(manager: 'FuseModManager', global_table) -> None:
    manager.register_module("simple", SimpleModule(global_table))
    manager.register_module("email", EmailModule(global_table))
    manager.register_module("cloudflareKV", CloudFlareKVModule(global_table))