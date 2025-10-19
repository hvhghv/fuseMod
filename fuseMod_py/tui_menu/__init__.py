from .emailMenu import register_email
from .cloudflareKVMenu import register_cloudflareKV


def register_menu(panel):
    register_email(panel, panel.add_menu("email_modules", "邮箱模块"))
    register_cloudflareKV(panel, panel.add_menu("cloudflareKV_modules", "CloudflareKV模块"))