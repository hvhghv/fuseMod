from ..VF_Tui import Panel, Menu
from .simpleMenuManager import SimpleMenuManager,register_simple_menu


def register_cloudflareKV(panel: Panel, menu:Menu):
    field_config = {
        'title': {'type': 'text', 'default': '添加新子项', 'flag': SimpleMenuManager.FLAG_SAVE_NOT_EMPTY},
        'account_id': {'type': 'text', 'default': '', 'flag': SimpleMenuManager.FLAG_SAVE_NOT_EMPTY},
        'namespace_id': {'type': 'text', 'default': '', 'flag': SimpleMenuManager.FLAG_SAVE_NOT_EMPTY},
        'api_key': {'type': 'text', 'default': '', 'flag': SimpleMenuManager.FLAG_SAVE_NOT_EMPTY},
        'key': {'type': 'password', 'default': '', 'flag': SimpleMenuManager.FLAG_SAVE_NOT_EMPTY},
        'updateTimeMin': {'type': 'int', 'default': 10, 'flag': 0},
    }
    
    formats = {
            'title': "添加新子项：{value}",
            'account_id': "账号ID：{value}",
            'namespace_id': "KV命名空间ID：{value}",
            'api_key': "API密钥：{value}",
            'key': "键值：{value}",
            'updateTimeMin': "更新间隔（分钟）：{value}",
        }
    
    register_simple_menu(panel, menu, field_config, formats, 'cloudflareKV')