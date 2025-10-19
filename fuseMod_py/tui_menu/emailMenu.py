# from ..VF_Tui import Panel, Menu, Item
# from typing import Dict
# import copy

# value_dict = {
#     "title" : "添加新子项",
#     "host" : "",
#     "port" : 465,
#     "account" : "",
#     "password" : "",
#     "sender" : "",
#     "sender_email" : "",
#     "receiver" : "",
#     "receiver_email" : "",
#     "subject": "",
#     "ssl": False,
#     "tls": False
# }

# def reset_menu(item_dict):
#     value_dict["title"] = "添加新子项"
#     value_dict["host"] = ""
#     value_dict["port"] = 465
#     value_dict["account"] = ""
#     value_dict["password"] = ""
#     value_dict["sender"] = ""
#     value_dict["sender_email"] = ""
#     value_dict["receiver"] = ""
#     value_dict["receiver_email"] = ""
#     value_dict["subject"] = ""
#     value_dict["ssl"] = False
#     value_dict["tls"] = False
#     reload_menu(item_dict)


# def reload_menu(item_dict):
#     item_dict['title'].set_name(f"选择项：{value_dict['title']}")
#     item_dict['host'].set_name(f"域名: {value_dict['host']}")
#     item_dict['port'].set_name(f"端口: {value_dict['port']}")
#     item_dict['account'].set_name(f"账号：{value_dict['account']}")
#     item_dict['password'].set_name("密码：" + "*"* len(value_dict["password"]))
#     item_dict['sender'].set_name(f"发件人：{value_dict['sender']}")
#     item_dict['sender_email'].set_name(f"发件人账号：{value_dict['sender_email']}")
#     item_dict['receiver'].set_name(f"收件人：{value_dict['receiver']}")
#     item_dict['receiver_email'].set_name(f"收件人账号：{value_dict['receiver_email']}")
#     item_dict['subject'].set_name(f"主题：{value_dict['subject']}")
#     item_dict['ssl'].set_name(f"启动SSL：{value_dict['ssl']}")
#     item_dict['tls'].set_name(f"启动TLS：{value_dict['tls']}")
    
# def save_item(panel: Panel, item_dict):
    
#     def check_invaild(item_list):
#         for i in item_list:
#             if value_dict[i] == "":
#                 return False
        
#         return True

#     if value_dict['title'] == "添加新子项":
#         return
    
#     if check_invaild(['title', 'host', 'account', 'password', 'sender', 'sender_email', 'receiver', 'receiver_email', 'subject']) == False:
#         return
    
#     config = panel.read_config("email")
    
#     instance_list_name = []
#     for instance in config["instances"]:
#         instance_list_name.append(instance["name"])
        
#     name = value_dict["title"]
#     argv = copy.copy(value_dict)
#     argv.pop("title")
    
#     if value_dict["title"] in instance_list_name:
#         index = instance_list_name.index(value_dict["title"])
#         config["instances"][index]["name"] = name
#         config["instances"][index]["argv"] = argv

#     else:
#         config["instances"].append({
#             "name": name,
#             "argv": argv
#         })

    
#     panel.write_config("email", config)

#     reset_menu(item_dict)
#     panel.draw()

# def choose_item(panel: Panel, menu:Menu, item_dict: Dict[str, Item]):
#     config = panel.read_config("email")
#     choose_list = ["添加新子项"]
#     for instance in config["instances"]:
#         choose_list.append(instance["name"])
    
#     index = choose_list.index(value_dict["title"])
    
#     def jump_late(ret):
        
#         if ret == None:
#             return
        
#         if ret == 0:
#             reset_menu(item_dict)
#         else:
#             ret -= 1
#             value_dict["title"] = config["instances"][ret]["name"]
#             value_dict["host"] = config["instances"][ret]["argv"]["host"]
#             value_dict["port"] = config["instances"][ret]["argv"]["port"]
#             value_dict["account"] = config["instances"][ret]["argv"]["account"]
#             value_dict["password"] = config["instances"][ret]["argv"]["password"]
#             value_dict["sender"] = config["instances"][ret]["argv"]["sender"]
#             value_dict["sender_email"] = config["instances"][ret]["argv"]["sender_email"]
#             value_dict["receiver"] = config["instances"][ret]["argv"]["receiver"]
#             value_dict["receiver_email"] = config["instances"][ret]["argv"]["receiver_email"]
#             value_dict["subject"] = config["instances"][ret]["argv"]["subject"]
#             value_dict["ssl"] = config["instances"][ret]["argv"]["ssl"]
#             value_dict["tls"] = config["instances"][ret]["argv"]["tls"]
            
#         reload_menu(item_dict)

    
#     panel.jump_checkbox(choose_list, index, jump_late)


# def reset_item(panel: Panel, item_dict, key):
    
#     def result(value):
        
#         if value == None:
#             return
        
#         if type(value_dict[key]) == int:
#             value = int(value)
        
#         value_dict[key] = value
#         reload_menu(item_dict)

#     panel.jump_input(result, str(value_dict[key]))
    
# def reset_item_choose(panel: Panel, item_dict, key):
#     def fin(value):
#         if value == None:
#             return

#         if value == 0:
#             value_dict[key] = True
#         else:
#             value_dict[key] = False

#         reload_menu(item_dict)
    
#     panel.jump_checkbox(["True", "False"], 0 if value_dict[key] == True else 1, fin)

# def delete_item(panel: Panel, item_dict):
#     config = panel.read_config("email")
#     to_delete_list = []
#     for instance in config["instances"]:
#         to_delete_list.append(instance["name"])
    
#     if value_dict['title'] not in to_delete_list:
#         reset_menu(item_dict)
#         return
    
#     try:
#         index = to_delete_list.index(value_dict['title'])
#     except:
#         reset_menu(item_dict)
#         return

#     def fin(input):
#         if (input != 'y'):
#             return
        
#         del config["instances"][index]
#         panel.write_config("email", config)
#         reset_menu(item_dict)
    
#     panel.jump_input(fin)

# def register_email(panel: Panel, menu:Menu):
    
#     item_dict = {}
#     item_dict['title'] = menu.add_item("email_title", f"选择项：{value_dict['title']}", lambda p, m, i, a: reset_item(panel, item_dict, 'title'))
    
#     menu.add_space()
#     item_dict['host'] = menu.add_item("email_host", f"域名: {value_dict['host']}", lambda p, m, i, a: reset_item(panel, item_dict, 'host'))
#     item_dict['port'] = menu.add_item("email_port", f"端口: {value_dict['port']}", lambda p, m, i, a: reset_item(panel, item_dict, 'port'))
#     item_dict['account'] = menu.add_item("email_account", f"账号：{value_dict['account']}", lambda p, m, i, a: reset_item(panel, item_dict, 'account'))
#     item_dict['password'] = menu.add_item("email_password", f"密码：", lambda p, m, i, a: reset_item(panel, item_dict, 'password'))
#     item_dict['sender'] = menu.add_item("email_sender", f"发件人：{value_dict['sender']}", lambda p, m, i, a: reset_item(panel, item_dict, 'sender'))
#     item_dict['sender_email'] = menu.add_item("email_sender_email", f"发件人账号：{value_dict['sender_email']}", lambda p, m, i, a: reset_item(panel, item_dict, 'sender_email'))
#     item_dict['receiver'] = menu.add_item("email_receiver", f"收件人：{value_dict['receiver']}", lambda p, m, i, a: reset_item(panel, item_dict, 'receiver'))
#     item_dict['receiver_email'] = menu.add_item("email_receiver_value", f"收件人账号：{value_dict['receiver_email']}", lambda p, m, i, a: reset_item(panel, item_dict, 'receiver_email'))
#     item_dict['subject'] = menu.add_item("email_subject", f"主题：{value_dict['subject']}", lambda p, m, i, a: reset_item(panel, item_dict, 'subject'))
#     item_dict['ssl'] = menu.add_item("email_enable_ssl", f"启动SSL：{value_dict['ssl']}", lambda p, m, i, a: reset_item_choose(panel, item_dict, 'ssl'))
#     item_dict['tls'] = menu.add_item("email_enable_tls", f"启动TLS：{value_dict['tls']}", lambda p, m, i, a: reset_item_choose(panel, item_dict, 'tls'))
    
#     menu.add_space()
    
#     menu.add_item("choose", "选取子项", lambda p, m, i, a: choose_item(panel, menu, item_dict))
#     menu.add_item("save", "保存子项", lambda p, m, i, a: save_item(panel, item_dict))
#     menu.add_item("del", "删除当前子项（输入'y'确定）", lambda p, m, i, a: delete_item(panel, item_dict))


from ..VF_Tui import Panel, Menu
from .simpleMenuManager import SimpleMenuManager,register_simple_menu

def register_email(panel: Panel, menu:Menu):

    field_config = {
        'title': {'type': 'text', 'default': '添加新子项', 'flag': SimpleMenuManager.FLAG_SAVE_NOT_EMPTY},
        'host': {'type': 'text', 'default': '', 'flag': SimpleMenuManager.FLAG_SAVE_NOT_EMPTY},
        'port': {'type': 'int', 'default': 476, 'flag': 0},
        'account': {'type': 'text', 'default': '', 'flag': SimpleMenuManager.FLAG_SAVE_NOT_EMPTY},
        'password': {'type': 'password', 'default': '', 'flag': SimpleMenuManager.FLAG_SAVE_NOT_EMPTY},
        'sender': {'type': 'text', 'default': '', 'flag': SimpleMenuManager.FLAG_SAVE_NOT_EMPTY},
        'sender_email': {'type': 'text', 'default': '', 'flag': SimpleMenuManager.FLAG_SAVE_NOT_EMPTY},
        'receiver': {'type': 'text', 'default': '', 'flag': SimpleMenuManager.FLAG_SAVE_NOT_EMPTY},
        'receiver_email': {'type': 'text', 'default': '', 'flag': SimpleMenuManager.FLAG_SAVE_NOT_EMPTY},
        'subject': {'type': 'text', 'default': '', 'flag': SimpleMenuManager.FLAG_SAVE_NOT_EMPTY},
        'ssl': {'type': 'bool', 'default': False, 'flag': 0},
        'tls': {'type': 'bool', 'default': False, 'flag': 0}
    }
    
    formats = {
            'title': "添加新子项{value}",
            'host': "域名：{value}",
            'port': "端口：{value}",
            'account': "账号：{value}",
            'password': "密码：{value}",
            'sender': "发件人：{value}",
            'sender_email': "发件人账号：{value}",
            'receiver': "收件人：{value}",
            'receiver_email': "收件人账号：{value}",
            'subject': "主题：{value}",
            'ssl': "启动SSL：{value}",
            'tls': "启动TLS：{value}"
        }
    
    register_simple_menu(panel, menu, field_config, formats, 'email')
