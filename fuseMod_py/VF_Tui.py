import curses
import os
import json
from typing import List, Tuple, Callable, Any, Dict, Optional

class Item:
    def __init__(self, id: str, name: str, callback: Optional[Callable[..., Any]], args: Any = None):
        self.id = id
        self.name = name
        self.callback = callback
        self.args = args
        self.is_divider = False
        self.is_space = False
    
    def set_name(self, name: str):
        self.name = name
    
    def set_callback(self, callback: Callable[..., Any], args: Any = None):
        self.callback = callback
        self.args = args

class Menu:
    def __init__(self, id: str, name: str, global_table: dict):
        self.id = id
        self.name = name
        self.items: List[Item] = []
        self.expanded = False
        self.global_table = global_table
    
    def set_name(self, name: str):
        self.name = name
    
    def add_item(self, id: str, name: str, callback: Callable[..., Any] = None, args: Any = None):
        item = Item(id, name, callback, args)
        self.items.append(item)
        return item
    
    def del_item(self, item: Item):
        if item in self.items:
            self.items.remove(item)
    
    def add_divider(self, name: str = ""):
        divider = Item("divider", name, None)
        divider.is_divider = True
        self.items.append(divider)
    
    def add_space(self):
        space = Item("space", "", None)
        space.is_space = True
        self.items.append(space)
    
    def get_global_table(self):
        return self.global_table
    
    def get_data_path(self, *paths):
        return os.path.join(self.get_global_table()["data_dir"], *paths)
    
    def read_config(self, name):
        with open(os.path.join(self.get_global_table()["config_dir"], f"{name}.json"), "r", encoding="utf-8") as f:
            return json.load(f)
        
    def write_config(self, name, obj):
        with open(os.path.join(self.get_global_table()["config_dir"], f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(obj, f)

class Panel(Menu):
    def __init__(self, config_dir, data_dir, id: str = "root", name: str = "Root Panel"):
        super().__init__(id, name, {
            "config_dir": config_dir,
            "data_dir": data_dir
        })
        self.menus: Dict[str, Menu] = {}
        self.selected_index = 0
        self.screen: curses.window = None # type: ignore
        self.input_mode = False
        self.multi_line_mode = False
        self.select_mode = False
        self.checkbox_mode = False
        self.input_text = ""
        self.select_list: List[str] = []
        self.select_default: List[bool] = []
        self.checkbox_list: List[str] = []
        self.checkbox_default: int = 0
        self.result = None
        self.running = True
        self.colors = {}
        self.jump_callback = None
        self.utf8inputMode = None
        self.utf8text = b''
    
    def add_menu(self, id: str, name: str):
        menu = Menu(id, name, self.global_table)
        self.menus[id] = menu
        self.add_item(id, name, self.toggle_menu, menu)
        return menu
    
    def del_menu(self, menu: Menu):
        if menu.id in self.menus:
            del self.menus[menu.id]
            # 从当前菜单项中移除
            for idx, item in enumerate(self.items):
                if item.id == menu.id:
                    self.items.pop(idx)
                    break
    
    def find_menu(self, id: str) -> Optional[Menu]:
        return self.menus.get(id)
    
    def find_item(self, id: str, menu_id: Optional[str] = None, menu: Optional[Menu] = None) -> Optional[Item]:
        if menu:
            for item in menu.items:
                if item.id == id:
                    return item
        elif menu_id:
            menu = self.find_menu(menu_id)
            if menu:
                return self.find_item(id, menu=menu)
        else:
            for item in self.items:
                if item.id == id:
                    return item
        return None
    
    def toggle_menu(self, panel, menu, item, args):
        if args.expanded:
            args.expanded = False
        else:
            args.expanded = True
        self.draw()
    
    def jump_input(self, callback, default = ""):
        self.jump_callback = callback
        self.input_text = default
        self.input_mode = True
        self.draw()
    
    def jump_inputRich(self, callback, default = "") -> str:
        self.jump_callback = callback
        self.input_text = default
        self.multi_line_mode = True
        self.draw()
    
    def jump_select(self, select_list: List[str], default: List[bool], callback):
        self.jump_callback = callback
        self.select_mode = True
        self.select_list = select_list
        self.select_default = default
        self.selected_index = 0
        self.draw()
    
    def jump_checkbox(self, select_list: List[str], default: int, callback):
        self.jump_callback = callback
        self.checkbox_mode = True
        self.checkbox_list = select_list
        self.checkbox_default = default
        self.selected_index = 0
        self.draw()
    
    def draw(self):
        if not self.screen:
            return
        
        self.screen.clear()
        height, width = self.screen.getmaxyx()
        
        if self.input_mode:
            self._draw_input_screen("单行输入")
            return
        
        if self.multi_line_mode:
            self._draw_multi_line_screen()
            return
        
        if self.select_mode:
            self._draw_select_screen("复选")
            return
        
        if self.checkbox_mode:
            self._draw_checkbox_screen("单选")
            return
        
        # 绘制顶部边框
        top_border = "╭" + "─" * (width - 2) + "╮"
        self.screen.addstr(0, 0, top_border, self.colors.get("border", curses.A_NORMAL))
        
        # 绘制标题
        title = f" {self.name} "
        title_x = max(0, (width - len(title)) // 2)
        self.screen.addstr(1, title_x, title, self.colors.get("title", curses.A_BOLD))
        
        # 绘制菜单项
        current_row = 3
        visible_items = []
        
        # 收集所有可见项
        for idx, item in enumerate(self.items):
            visible_items.append((item, 0))
            menu = self.menus.get(item.id)
            if menu:
                # 无论菜单是否展开，都在菜单项后添加空行
                visible_items.append((Item("space", "", None), 0))
                if menu.expanded:
                    for sub_item in menu.items:
                        visible_items.append((sub_item, 1))
                    # 在子菜单项后添加空行
                    visible_items.append((Item("space", "", None), 0))
        
        # 绘制可见项
        for idx, (item, indent_level) in enumerate(visible_items):
            if current_row >= height - 3:
                break
            
            if item.is_divider:
                # 绘制分割线
                line = "├" + "─" * (width - 2) + "┤"
                self.screen.addstr(current_row, 0, line, self.colors.get("border", curses.A_NORMAL))
                
                # 在分割线上添加名称
                if item.name:
                    name_text = f" {item.name} "
                    name_x = max(0, (width - len(name_text)) // 2)
                    self.screen.addstr(current_row, name_x, name_text, self.colors.get("divider", curses.A_DIM))
                
                current_row += 1
            elif item.is_space:
                # 空行
                current_row += 1
            else:
                # 普通菜单项
                prefix = "❯ " if idx == self.selected_index else "  "
                indent = "  " * indent_level
                text = prefix + indent + item.name
                
                # 如果是菜单项且已展开，添加展开标记
                menu = self.menus.get(item.id)
                if menu and menu.expanded:
                    text = prefix + indent + "▼ " + item.name
                elif menu:
                    text = prefix + indent + "▶ " + item.name
                
                # 设置颜色属性
                if idx == self.selected_index:
                    attr = self.colors.get("selected", curses.A_REVERSE)
                elif menu:
                    # 菜单项使用特殊颜色
                    attr = self.colors.get("menu", curses.A_BOLD)
                else:
                    attr = self.colors.get("normal", curses.A_NORMAL)
                
                self.screen.addstr(current_row, 2, text, attr)
                current_row += 1
        
        # 绘制底部边框
        bottom_border = "╰" + "─" * (width - 2) + "╯"
        self.screen.addstr(height - 3, 0, bottom_border, self.colors.get("border", curses.A_NORMAL))
        
        # 绘制底部帮助信息
        help_text = "↑/↓: 导航  Enter: 选择  Ctrl+D: 退出"
        help_x = max(0, (width - len(help_text)) // 2)
        self.screen.addstr(height - 2, help_x, help_text, self.colors.get("help", curses.A_DIM))
        
        self.screen.refresh()
    
    def _draw_input_screen(self, title: str):
        height, width = self.screen.getmaxyx()
        
        # 绘制顶部边框
        top_border = "╭" + "─" * (width - 2) + "╮"
        self.screen.addstr(0, 0, top_border, self.colors.get("border", curses.A_NORMAL))
        
        # 绘制标题
        title_x = max(0, (width - len(title)) // 2)
        self.screen.addstr(1, title_x, title, self.colors.get("title", curses.A_BOLD))
        
        # 绘制输入框
        input_width = min(40, width - 6)
        input_x = max(2, (width - input_width) // 2)
        
        # 绘制输入框顶部
        self.screen.addstr(3, input_x - 1, "╭" + "─" * (input_width) + "╮", self.colors.get("border", curses.A_NORMAL))
        
        # 输入区域
        self.screen.addstr(4, input_x - 1, "│", self.colors.get("border", curses.A_NORMAL))
        self.screen.addstr(4, input_x + input_width, "│", self.colors.get("border", curses.A_NORMAL))
        
        # 显示当前输入内容
        display_text = self.input_text.ljust(input_width - 2)
        if len(display_text) > input_width - 2:
            display_text = display_text[:input_width - 5] + "..."
        self.screen.addstr(4, input_x, display_text, self.colors.get("input", curses.A_NORMAL))
        
        # 绘制输入框底部
        self.screen.addstr(5, input_x - 1, "╰" + "─" * (input_width) + "╯", self.colors.get("border", curses.A_NORMAL))
        
        # 绘制底部边框
        bottom_border = "╰" + "─" * (width - 2) + "╯"
        self.screen.addstr(height - 3, 0, bottom_border, self.colors.get("border", curses.A_NORMAL))
        
        # 绘制底部帮助信息
        help_text = "Enter: 确认  ESC: 取消"
        help_x = max(0, (width - len(help_text)) // 2)
        self.screen.addstr(height - 2, help_x, help_text, self.colors.get("help", curses.A_DIM))
        
        # 绘制光标
        cursor_pos = min(len(self.input_text), input_width - 2)
        self.screen.move(4, input_x + cursor_pos)
        
        self.screen.refresh()
    
    def _draw_multi_line_screen(self):
        height, width = self.screen.getmaxyx()
        title = "多行输入"
        
        # 绘制顶部边框
        top_border = "╭" + "─" * (width - 2) + "╮"
        self.screen.addstr(0, 0, top_border, self.colors.get("border", curses.A_NORMAL))
        
        # 绘制标题
        title_x = max(0, (width - len(title)) // 2)
        self.screen.addstr(1, title_x, title, self.colors.get("title", curses.A_BOLD))
        
        # 绘制输入框
        input_width = min(60, width - 6)
        input_height = min(10, height - 8)
        input_x = max(2, (width - input_width) // 2)
        input_y = 3
        
        # 绘制边框
        self.screen.addstr(input_y, input_x - 1, "╭" + "─" * (input_width) + "╮", self.colors.get("border", curses.A_NORMAL))
        for i in range(1, input_height - 1):
            self.screen.addstr(input_y + i, input_x - 1, "│", self.colors.get("border", curses.A_NORMAL))
            self.screen.addstr(input_y + i, input_x + input_width, "│", self.colors.get("border", curses.A_NORMAL))
        self.screen.addstr(input_y + input_height - 1, input_x - 1, "╰" + "─" * (input_width) + "╯", self.colors.get("border", curses.A_NORMAL))
        
        # 显示当前输入内容
        lines = self.input_text.split('\n')
        for i, line in enumerate(lines[:input_height - 2]):
            display_line = line.ljust(input_width - 2)[:input_width - 2]
            self.screen.addstr(input_y + 1 + i, input_x, display_line, self.colors.get("input", curses.A_NORMAL))
        
        # 绘制底部边框
        bottom_border = "╰" + "─" * (width - 2) + "╯"
        self.screen.addstr(height - 3, 0, bottom_border, self.colors.get("border", curses.A_NORMAL))
        
        # 绘制底部帮助信息
        help_text = "Enter: 换行  F1: 确认  ESC: 取消"
        help_x = max(0, (width - len(help_text)) // 2)
        self.screen.addstr(height - 2, help_x, help_text, self.colors.get("help", curses.A_DIM))
        
        self.screen.refresh()
    
    def _draw_select_screen(self, title: str):
        height, width = self.screen.getmaxyx()
        
        # 绘制顶部边框
        top_border = "╭" + "─" * (width - 2) + "╮"
        self.screen.addstr(0, 0, top_border, self.colors.get("border", curses.A_NORMAL))
        
        # 绘制标题
        title_x = max(0, (width - len(title)) // 2)
        self.screen.addstr(1, title_x, title, self.colors.get("title", curses.A_BOLD))
        
        # 绘制选项
        start_y = 3
        
        for idx, option in enumerate(self.select_list):
            if start_y + idx >= height - 4:
                break
            
            checkbox = "✓" if self.select_default[idx] else " "
            text = f"  [{checkbox}] {option}"
            if idx == self.selected_index:
                attr = self.colors.get("selected", curses.A_REVERSE)
            else:
                attr = self.colors.get("menu", curses.A_BOLD) if idx % 2 == 0 else self.colors.get("normal", curses.A_NORMAL)
            
            text_x = 20
            self.screen.addstr(start_y + idx, text_x, text, attr)
        
        # 绘制底部边框
        bottom_border = "╰" + "─" * (width - 2) + "╯"
        self.screen.addstr(height - 3, 0, bottom_border, self.colors.get("border", curses.A_NORMAL))
        
        # 绘制底部帮助信息
        help_text = "↑/↓: 导航  Space: 选择/取消  Enter: 确认  ESC: 取消"
        help_x = max(0, (width - len(help_text)) // 2)
        self.screen.addstr(height - 2, help_x, help_text, self.colors.get("help", curses.A_DIM))
        
        self.screen.refresh()
    
    def _draw_checkbox_screen(self, title: str):
        height, width = self.screen.getmaxyx()
        
        # 绘制顶部边框
        top_border = "╭" + "─" * (width - 2) + "╮"
        self.screen.addstr(0, 0, top_border, self.colors.get("border", curses.A_NORMAL))
        
        # 绘制标题
        title_x = max(0, (width - len(title)) // 2)
        self.screen.addstr(1, title_x, title, self.colors.get("title", curses.A_BOLD))
        
        # 绘制选项
        start_y = 3
        
        for idx, option in enumerate(self.checkbox_list):
            if start_y + idx >= height - 4:
                break
            
            checkbox = "●" if idx == self.checkbox_default else " "
            text = f"  [{checkbox}] {option}"
            if idx == self.selected_index:
                attr = self.colors.get("selected", curses.A_REVERSE)
            else:
                attr = self.colors.get("menu", curses.A_BOLD) if idx % 2 == 0 else self.colors.get("normal", curses.A_NORMAL)
            
            text_x = 20
            self.screen.addstr(start_y + idx, text_x, text, attr)
        
        # 绘制底部边框
        bottom_border = "╰" + "─" * (width - 2) + "╯"
        self.screen.addstr(height - 3, 0, bottom_border, self.colors.get("border", curses.A_NORMAL))
        
        # 绘制底部帮助信息
        help_text = "↑/↓: 导航  Space: 选择  Enter: 确认  ESC: 取消"
        help_x = max(0, (width - len(help_text)) // 2)
        self.screen.addstr(height - 2, help_x, help_text, self.colors.get("help", curses.A_DIM))
        
        self.screen.refresh()
    
    def handle_input(self, stdscr):
        self.screen = stdscr
        curses.curs_set(0)  # 隐藏光标
        stdscr.keypad(True)  # 启用特殊键
        stdscr.nodelay(False)
        
        # 初始化颜色
        if curses.has_colors():
            curses.start_color()
            # 定义颜色对 - 使用更美观的配色方案
            curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)    # 标题 - 青色
            curses.init_pair(2, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # 菜单 - 洋红色
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # 边框 - 黄色
            curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)   # 输入 - 绿色
            curses.init_pair(5, curses.COLOR_BLUE, curses.COLOR_BLACK)    # 分割线 - 蓝色
            curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_CYAN)   # 选中项 - 青色背景
            curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)   # 正常 - 白色
            curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_WHITE)   # 帮助文本 - 白底黑字
            
            self.colors = {
                "title": curses.color_pair(1) | curses.A_BOLD,
                "menu": curses.color_pair(2) | curses.A_BOLD,  # 洋红色加粗
                "border": curses.color_pair(3),
                "input": curses.color_pair(4),
                "divider": curses.color_pair(5),
                "selected": curses.color_pair(6),
                "normal": curses.color_pair(7),
                "help": curses.color_pair(8)
            }
        else:
            # 无颜色支持时的回退
            self.colors = {
                "title": curses.A_BOLD,
                "menu": curses.A_BOLD,
                "border": curses.A_NORMAL,
                "input": curses.A_NORMAL,
                "divider": curses.A_DIM,
                "selected": curses.A_REVERSE,
                "normal": curses.A_NORMAL,
                "help": curses.A_DIM
            }
        
        self.draw()
        
        while self.running:
            key = stdscr.getch()
            
            # 全局快捷键：Ctrl+D 退出程序
            if key == 4:  # Ctrl+D
                self.running = False
                break
            
            if self.input_mode:
                self._handle_input_key(key)
            elif self.multi_line_mode:
                self._handle_multi_line_key(key)
            elif self.select_mode:
                self._handle_select_key(key)
            elif self.checkbox_mode:
                self._handle_checkbox_key(key)
            else:
                self._handle_normal_key(key)
    
    def _handle_normal_key(self, key):
        # 收集所有可见项
        visible_items = []
        for item in self.items:
            visible_items.append(item)
            menu = self.menus.get(item.id)
            if menu:
                # 无论菜单是否展开，都在菜单项后添加空行
                visible_items.append(Item("space", "", None))
                if menu.expanded:
                    for sub_item in menu.items:
                        visible_items.append(sub_item)
                    # 在子菜单项后添加空行
                    visible_items.append(Item("space", "", None))
        
        max_index = len(visible_items) - 1
        
        if key == curses.KEY_UP:
            self.selected_index = max(0, self.selected_index - 1)
        elif key == curses.KEY_DOWN:
            self.selected_index = min(max_index, self.selected_index + 1)
        elif key == curses.KEY_ENTER or key == 10 or key == 13:
            if self.selected_index < len(visible_items):
                item = visible_items[self.selected_index]
                
                # 检查是否是菜单项
                menu = self.menus.get(item.id)
                if menu:
                    # 菜单项 - 展开/折叠
                    menu.expanded = not menu.expanded
                elif item.callback:
                    # 普通项 - 执行回调
                    item.callback(self, None, item, item.args)
        
        self.draw()
    
    def _handle_input_key(self, key):
        if key == curses.KEY_ENTER or key == 10 or key == 13:
            self.result = self.input_text
            self.input_mode = False
        elif key == 27:  # ESC
            self.result = None
            self.input_mode = False
        elif key == curses.KEY_BACKSPACE or key == 127:
            self.input_text = self.input_text[:-1]

        elif key >= 32 and key <= 126:  # 可打印字符
            self.input_text += chr(key)
            
        elif (key >> 6) == 2:
            if self.utf8inputMode != None:
                self.utf8inputMode -= 1
                self.utf8text = self.utf8text + int.to_bytes(key, 1, 'big')

            if self.utf8inputMode == 0:
                try:
                    self.input_text += self.utf8text.decode()
                except:
                    pass
            
            if self.utf8inputMode == None or self.utf8inputMode <= 0:
                self.utf8inputMode = None
                self.utf8text = b""
            
        
        elif (key >> 5) == 6:
            if self.utf8inputMode == None:
                self.utf8inputMode = 1
                self.utf8text = self.utf8text + int.to_bytes(key, 1, 'big')
            else:
                self.utf8inputMode = None
                self.utf8text = b""
        
        elif (key >> 4) == 14:
            if self.utf8inputMode == None:
                self.utf8inputMode = 2
                self.utf8text = self.utf8text + int.to_bytes(key, 1, 'big')
            else:
                self.utf8inputMode = None
                self.utf8text = b""
        
        elif (key >> 3) == 30:
            if self.utf8inputMode == None:
                self.utf8inputMode = 3
                self.utf8text = self.utf8text + int.to_bytes(key, 1, 'big')
            else:
                self.utf8inputMode = None
                self.utf8text = b""
        
        
        if self.input_mode == False and self.jump_callback:
            self.jump_callback(self.result)
            self.jump_callback = None
        
        self.draw()
    
    def _handle_multi_line_key(self, key):
        if key == curses.KEY_F1:  # F1确认
            self.result = self.input_text
            self.multi_line_mode = False
        elif key == curses.KEY_ENTER or key == 10 or key == 13:
            self.input_text += '\n'
        elif key == 27:  # ESC
            self.result = None
            self.multi_line_mode = False
        elif key == curses.KEY_BACKSPACE or key == 127:
            if self.input_text.endswith('\n'):
                self.input_text = self.input_text[:-1]
            self.input_text = self.input_text[:-1]
        elif key >= 32 and key <= 126:  # 可打印字符
            self.input_text += chr(key)
            
        if self.multi_line_mode == False and self.jump_callback:
            self.jump_callback(self.result)
            self.jump_callback = None
        
        self.draw()
    
    def _handle_select_key(self, key):
        if key == curses.KEY_UP:
            self.selected_index = max(0, self.selected_index - 1)
        elif key == curses.KEY_DOWN:
            self.selected_index = min(len(self.select_list) - 1, self.selected_index + 1)
        elif key == ord(' '):
            if 0 <= self.selected_index < len(self.select_default):
                self.select_default[self.selected_index] = not self.select_default[self.selected_index]
        elif key == curses.KEY_ENTER or key == 10 or key == 13:
            self.result = self.select_default
            self.select_mode = False
        elif key == 27:  # ESC
            self.result = None
            self.select_mode = False
        
        if self.select_mode == False and self.jump_callback:
            self.jump_callback(self.result)
            self.jump_callback = None
        
        self.draw()
    
    def _handle_checkbox_key(self, key):
        if key == curses.KEY_UP:
            self.selected_index = max(0, self.selected_index - 1)
        elif key == curses.KEY_DOWN:
            self.selected_index = min(len(self.checkbox_list) - 1, self.selected_index + 1)
        elif key == ord(' '):
            self.checkbox_default = self.selected_index
        elif key == curses.KEY_ENTER or key == 10 or key == 13:
            self.result = self.checkbox_default
            self.checkbox_mode = False
        elif key == 27:  # ESC
            self.result = None
            self.checkbox_mode = False
        
        if self.checkbox_mode == False and self.jump_callback:
            self.jump_callback(self.result)
            self.jump_callback = None
        
        self.draw()

# 示例使用
# def main(stdscr: curses.window):
#     # 创建面板
#     panel = Panel("main", "系统设置")
    
#     # 添加基本设置菜单
#     basic_menu = panel.add_menu("basic", "基本设置")
#     basic_menu.add_item("item1", "内容1", lambda p, m, i, a: print("内容1被选择"))
#     basic_menu.add_item("item2", "内容2", lambda p, m, i, a: print("内容2被选择"))
#     basic_menu.add_item("item3", "内容3", lambda p, m, i, a: print("内容3被选择"))
    
#     # 添加高级设置菜单
#     advanced_menu = panel.add_menu("advanced", "高级设置")
#     advanced_menu.add_item("adv1", "高级内容1", lambda p, m, i, a: print("高级内容1被选择"))
#     advanced_menu.add_item("adv2", "高级内容2", lambda p, m, i, a: print("高级内容2被选择"))
    
#     # 添加其他功能项
#     panel.add_divider("功能")
#     panel.add_item("input", "单行输入", lambda p, m, i, a: p.jump_input())
#     panel.add_item("select", "复选", lambda p, m, i, a: p.jump_select(["选项1", "选项2", "选项3"], [True, False, True]))
#     panel.add_item("checkbox", "单选", lambda p, m, i, a: p.jump_checkbox(["选项A", "选项B", "选项C"], 0))
#     panel.add_item("rich", "多行输入", lambda p, m, i, a: p.jump_inputRich())
#     panel.add_item("exit", "退出", lambda p, m, i, a: exit(0))
    
#     # 启动TUI
#     panel.handle_input(stdscr)

