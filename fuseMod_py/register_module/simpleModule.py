# 示例使用
import asyncio
from ..VF_File import VF_File
from ..VF_Module import VF_Module
from typing import Optional, List, Dict, Any, Callable, Tuple

class SimpleFile(VF_File):
    def __init__(self, **kwargs) -> None:
        super().__init__(VF_File.FLAG_WRITE | VF_File.FLAG_READ)
        self.content = b""
        self.read_event = asyncio.Event()
    
    def write(self, buffer: bytes, offset: int) -> None:
        # 简单的写入实现
        if offset + len(buffer) > len(self.content):
            self.content += b"\0" * (offset + len(buffer) - len(self.content))
        self.content = self.content[:offset] + buffer + self.content[offset + len(buffer):]
        self.read_event.set()

    async def read(self) -> bytes:
        await self.read_event.wait()
        self.read_event.clear()
        return b"hello world"

    async def rm(self) -> None:
        # 简单的删除实现
        self.content = b""


class SimpleModuleChild(VF_Module):
    def __init__(self, global_table) -> None:
        super().__init__(global_table)
        self.register_file("child_file.txt")

    def create_file(self, name: str, kwargs: Dict[str, Any]) -> VF_File:
        return SimpleFile(**kwargs)

# 创建一个具体的模块实现
class SimpleModule(VF_Module):

    def __init__(self, global_table) -> None:
        super().__init__(global_table)
        self.register_module("child", SimpleModuleChild(global_table))
        self.register_file("file1.txt")

    def create_file(self, name: str, kwargs: Dict[str, Any]) -> VF_File:
        return SimpleFile(**kwargs)