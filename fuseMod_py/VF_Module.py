from typing import Optional, List, Tuple, Dict, Any, Callable
from .VF_File import VF_File
from .VF_Tools import path_parse
import json
import os

class VF_Module():
    """虚拟文件模块基类"""
    
    def __init__(self, global_table: Dict, enableDebug=False) -> None:
        self.register_module_table: Dict[str, VF_Module] = {}
        self.register_file_table: Dict[str, VF_File] = {}
        self.global_table = global_table
        self.debug_mode = enableDebug

    def get_global_table(self) -> Dict[str, Any]:
        return self.global_table

    def get_data_path(self, *paths):
        return os.path.join(self.get_global_table()["data_dir"], *paths)
    
    def read_config(self, name):
        with open(os.path.join(self.get_global_table()["config_dir"], f"{name}.json"), "r", encoding="utf-8") as f:
            return json.load(f)
        
    def write_config(self, name, obj):
        with open(os.path.join(self.get_global_table()["config_dir"], f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(obj, f)
    
    def register_module(self, name: str, module: 'VF_Module') -> None:
        """注册模块"""
        self.register_module_table[name] = module
        module.debug_mode = self.debug_mode

    def register_file(self, name: str, kwargs: Dict[str, Any] = {}) -> None:
        """注册文件"""

        file = self.create_file(name, kwargs)

        if file is not None:
            self.register_file_table[name] = file
        else:
            raise ValueError(f"Failed to create file: {name}")

    def tree_module(self, tree_list: Optional[List[Tuple[str, 'VF_Module']]] = None, 
             callback: Optional[Callable[[str, 'VF_Module'], None]] = None, 
             prefix: str = "") -> None:
        """遍历模块树"""
        for k, v in self.register_module_table.items():
            full_path = f"{prefix}/{k}"
            
            if tree_list is not None:
                tree_list.append((full_path, v))

            if callback is not None:
                callback(full_path, v)
            
            v.tree_module(tree_list, callback, full_path)

    def tree_file(self, tree_list: Optional[List[Tuple[str, VF_File]]] = None, 
             callback: Optional[Callable[[str, VF_File], None]] = None, prefix: str = "") -> None:

        for k, v in self.register_file_table.items():
            full_path = f"{prefix}/{k}"

            if tree_list is not None:
                tree_list.append((full_path, v))

            if callback is not None:
                callback(full_path, v)

        self.tree_module(callback = lambda path, module: module.tree_file(tree_list, callback, path), prefix=prefix)
    
    def create(self, path: str, kwargs: Dict[str, Any] = {}) -> Optional[VF_File]:
        """创建文件"""
        parsed = path_parse(path)
        if parsed is None:
            return None
        
        name, subPath = parsed
        
        if subPath == "/":
            file = self.create_file(name, kwargs)
        else:
            if name not in self.register_module_table:
                return None
            file = self.register_module_table[name].create(subPath, kwargs)
        
        return file
    
    def create_file(self, name: str, kwargs: Dict[str, Any]) -> Optional[VF_File]:
        """创建文件抽象方法"""
        return None