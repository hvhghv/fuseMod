import asyncio



class VF_File():
    """虚拟文件基类"""

    FLAG_READ = (1 << 0)
    FLAG_WRITE = (1 << 1)
    FLAG_COPY_ON_WRITE = (1 << 3)

    def __init__(self, flag) -> None:
        self.Flag = flag

    def write(self, buffer: bytes, offset: int) -> None:
        """写入文件"""
        pass
    
    async def read(self) -> bytes:
        """读取文件，默认永久阻塞"""
        await asyncio.Event().wait()
        return b''
    
    async def readAppend(self) -> bytes:
        """追加读取文件，默认永久阻塞"""
        await asyncio.Event().wait()
        return b''
    
    async def rm(self) -> None:
        """删除文件"""
        pass
    
    def isAvailableRead(self) -> bool:
        """检查是否可读"""
        return self.Flag & self.FLAG_READ != 0
    
    def isAvailableWrite(self) -> bool:
        """检查是否可写"""
        return self.Flag & self.FLAG_WRITE != 0

    def isCopyOnWrite(self) -> bool:
        return self.Flag & self.FLAG_COPY_ON_WRITE != 0
    
    def getFlag(self) -> int:
        """获取文件标志"""
        return self.Flag