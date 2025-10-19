from ..VF_Tui import Panel, Menu, Item
from typing import Dict, Any, Callable, List, Optional
import copy

class SimpleMenuManager:
    
    FLAG_SAVE_NOT_EMPTY = (1 << 0)
    
    def __init__(self, panel: Panel, menu: Menu, field_config, formats, config_name: str):
        self.panel = panel
        self.menu = menu
        self.config_name = config_name
        self.item_dict = {}
        self.field_config = field_config
        self.formats = formats
        self.value_dict = self.generate_value_dict(field_config)
        self.initial_values = copy.deepcopy(self.value_dict)
        self.register(config_name, field_config)
        
    def generate_value_dict(self, field_config:dict):
        value_dict = {}
        for k, v in field_config.items():
            value_dict[k] = v['default']
        
        return value_dict
    
    def reset_menu(self):
        """重置菜单到初始状态"""
        self.value_dict.clear()
        self.value_dict.update(copy.deepcopy(self.initial_values))
        self.reload_menu()
    
    def reload_menu(self):
        """重新加载菜单显示"""
        for key, item in self.item_dict.items():
            if key in self.value_dict:
                value = self.value_dict[key]
                if key == 'password':
                    display_value = "*" * len(value)
                else:
                    display_value = str(value)
                
                # 获取显示名称格式
                display_format = self.get_display_format(key)
                item.set_name(display_format.format(value=display_value))
    
    def get_display_format(self, key: str) -> str:
        """获取字段的显示格式"""
        
        return self.formats.get(key, "{key}: {value}".format(key=key, value="{value}"))
    
    def save_item(self):
        """保存当前项到配置"""

        
        for k, v in self.value_dict.items():
            if k == 'title' and v == '添加新子项':
                return
            
            if (self.field_config[k]["flag"] & SimpleMenuManager.FLAG_SAVE_NOT_EMPTY) and v == "":
                return

        
        config = self.panel.read_config(self.config_name)
        
        instance_list_name = []
        for instance in config.get("instances", []):
            instance_list_name.append(instance["name"])
        
        name = self.value_dict.get("title", "未命名")
        
        # 创建参数副本，排除标题
        argv = copy.copy(self.value_dict)
        if "title" in argv:
            argv.pop("title")
        
        # 更新或添加实例
        if name in instance_list_name:
            index = instance_list_name.index(name)
            config["instances"][index]["name"] = name
            config["instances"][index]["argv"] = argv
        else:
            if "instances" not in config:
                config["instances"] = []
            config["instances"].append({
                "name": name,
                "argv": argv
            })
        
        self.panel.write_config(self.config_name, config)
        self.reset_menu()
        self.panel.draw()
    
    def choose_item(self):
        """选择已有项"""
        config = self.panel.read_config(self.config_name)
        choose_list = ["添加新子项"]
        
        for instance in config.get("instances", []):
            choose_list.append(instance["name"])
        
        current_title = self.value_dict.get("title", "添加新子项")
        index = choose_list.index(current_title) if current_title in choose_list else 0
        
        def jump_callback(ret):
            if ret is None:
                return
            
            if ret == 0:
                self.reset_menu()
            else:
                ret -= 1
                instance_data = config["instances"][ret]
                self.value_dict["title"] = instance_data["name"]
                
                # 更新所有字段
                for key in self.value_dict.keys():
                    if key in instance_data["argv"]:
                        self.value_dict[key] = instance_data["argv"][key]
                
            self.reload_menu()
        
        self.panel.jump_checkbox(choose_list, index, jump_callback)
    
    def reset_item(self, key: str):
        """重置单个项的值"""
        def result(value):
            if value is None:
                return
            
            original_type = type(self.value_dict[key])
            if original_type == int:
                try:
                    value = int(value)
                except ValueError:
                    return
            
            self.value_dict[key] = value
            self.reload_menu()
        
        self.panel.jump_input(result, str(self.value_dict[key]))
    
    def reset_item_choose(self, key: str):
        """重置布尔类型项的值"""
        def fin(value):
            if value is None:
                return

            self.value_dict[key] = (value == 0)
            self.reload_menu()
        
        current_index = 0 if self.value_dict[key] else 1
        self.panel.jump_checkbox(["True", "False"], current_index, fin)
    
    def delete_item(self):
        """删除当前项"""
        config = self.panel.read_config(self.config_name)
        to_delete_list = []
        
        for instance in config.get("instances", []):
            to_delete_list.append(instance["name"])
        
        current_title = self.value_dict.get("title", "")
        if current_title not in to_delete_list:
            self.reset_menu()
            return
        
        try:
            index = to_delete_list.index(current_title)
        except ValueError:
            self.reset_menu()
            return

        def fin(input_text):
            if input_text != 'y':
                return
            
            del config["instances"][index]
            self.panel.write_config(self.config_name, config)
            self.reset_menu()
        
        self.panel.jump_input(fin)
    
    def register(self, config_name, field_config):

        # 注册字段菜单项
        for field_name, config in field_config.items():
            if field_name in self.value_dict:
                value = self.value_dict[field_name]
                if config['type'] == 'password':
                    display_value = "*" * len(value)
                    action = self.reset_item
                
                elif config['type'] == 'bool':
                    display_value = str(value)
                    action = self.reset_item_choose
                else:
                    display_value = str(value)
                    action = self.reset_item
                
                
                display_text = self.get_display_format(field_name).format(value=display_value)
                self.item_dict[field_name] = self.menu.add_item(
                    f"{self}_{field_name}", 
                    display_text, 
                    lambda p, m, i, a: a[0](a[1]),
                    (action, field_name)
                )
        
        self.menu.add_space()
        
        # 注册操作菜单项
        self.menu.add_item(f"{config_name}_choose", "选取子项", lambda p, m, i, a: self.choose_item())
        self.menu.add_item(f"{config_name}_save", "保存子项", lambda p, m, i, a: self.save_item())
        self.menu.add_item(f"{config_name}_del", "删除当前子项（输入'y'确定）", 
                    lambda p, m, i, a: self.delete_item())
        
        # 初始加载菜单
        self.reload_menu()


def register_simple_menu(panel: Panel, menu: Menu, field_config, formats, config_name):
    SimpleMenuManager(panel, menu, field_config, formats, config_name)