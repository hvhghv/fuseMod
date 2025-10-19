import asyncio
from logging import config
import aiofiles
import struct
import os
from typing import Optional, Dict, Any
from .VF_Module import VF_Module
from .VF_File import VF_File
from .VF_Tools import crc16_ccitt
from .VF_Defined import ERR_ALREADY_EXISTS, ERR_NOT_FOUND, ERR_INVALID_OPERATION, PACKET_HEADER, PACKET_TAIL, PACKET_MAX_SIZE, PACKET_MIN_SIZE

class FuseModManager(VF_Module):
    """FUSE 模块管理器"""
    
    def __init__(self, config_dir, data_dir, enableDebug) -> None:
        global_table = {
            "config_dir": config_dir,
            "data_dir": data_dir
        }

        super().__init__(global_table, enableDebug)
        self.file_cache_table: Dict[str, VF_File] = {}
        self.debug_mode = False
        self.pipe_in = None
        self.pipe_out = None
        self.process: Optional[asyncio.subprocess.Process] = None
        self.running = False
        self.pending_requests: Dict[int, asyncio.Future] = {}
        self.request_id = 0
    
    async def init(self, mount_point) -> "Optional[FuseModManager]":
        """初始化方法"""
        # 如果不存在 mount_point/modules 则创建
        mod_dir = os.path.join(mount_point, "modules")
        pipe_in_path = os.path.join(mount_point, "FuseModPipeIn")
        pipe_out_path = os.path.join(mount_point, "FuseModPipeOut")
        fusemod_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuseMod")

        try:
            os.makedirs(mod_dir, exist_ok=True)
        except Exception as e:
            if self.debug_mode:
                print(f"Error creating modules directory {mod_dir}: {e}")

        # 启动子进程，使用本py文件同目录下的fuseMod
        self.process = await asyncio.create_subprocess_exec(fusemod_path, pipe_in_path, pipe_out_path, mod_dir, "-f")

        # 等待管道创建
        await asyncio.sleep(1)

        # 异步打开命名管道，使用mount_point路径
        self.pipe_in = await aiofiles.open(pipe_in_path, "wb")
        self.pipe_out = await aiofiles.open(pipe_out_path, "rb")
        self.running = True
        return self
    
    async def fuse_mod_input(self, type: int, data: bytes) -> bool:
        """发送数据到 FUSE 模块"""

        if not self.running:
            return False

        # 构建数据包
        header = PACKET_HEADER
        size = len(data)
        size_bytes = struct.pack("<H", size)
        packet_without_crc = header + struct.pack("<H", type) + size_bytes + data
        crc = crc16_ccitt(packet_without_crc)
        
        crc_bytes = struct.pack("<H", crc)
        packet = packet_without_crc + crc_bytes + PACKET_TAIL

        if self.debug_mode:
            print(f"py send: {packet.hex()}, crc: {crc}, hex: {hex(crc)}")
        
        try:
            # 写入数据
            await self.pipe_in.write(packet) # type: ignore
            await self.pipe_in.flush() # type: ignore
            
            # 创建等待响应的事件
            request_id = self.request_id
            self.request_id += 1
            future = asyncio.Future()
            self.pending_requests[request_id] = future
            
            # 等待响应或超时
            try:
                await asyncio.wait_for(future, timeout=3.0)
                return True
            except asyncio.TimeoutError:
                if self.debug_mode:
                    print(f"Timeout waiting for response to type {type}")
                await self.cleanup()
                return False
            except Exception as e:
                print(e)
                raise e
                
        except Exception as e:
            if self.debug_mode:
                print(f"Error writing to pipe: {e}")
            await self.cleanup()
            return False
    
    async def listen(self) -> None:
        """监听来自 FUSE 模块的数据"""
        while self.running:
            try:
                # 读取包头
                header = await self.pipe_out.read(6) # type: ignore
                if len(header) < 6:
                    await asyncio.sleep(0.1)
                    continue

                if header[0:2] != b"\x54\x02":
                    # 无效包头，跳过
                    continue

                type_byte, size = struct.unpack("<HH", header[2:6])

                # 读取数据
                data = await self.pipe_out.read(size) # type: ignore
                if len(data) < size:
                    # 数据不足，跳过
                    continue
                
                # 读取CRC和尾部
                crc_data = await self.pipe_out.read(4) # type: ignore
                if len(crc_data) < 4:
                    # 数据不足，跳过
                    continue
                
                crc_received = struct.unpack("<H", crc_data[0:2])[0]
                tail = crc_data[2:4]
                
                if tail != PACKET_TAIL:
                    # 无效尾部，跳过
                    continue
                
                # 验证CRC
                packet_without_crc = header + data
                crc_calculated = crc16_ccitt(packet_without_crc)

                if self.debug_mode:
                    print(f"py recv: {(header + data + crc_data).hex()}")

                if crc_received != crc_calculated:
                    # CRC 不匹配，跳过
                    continue

                if type_byte == 0x07:
                    # 文件写入请求
                    await self.handle_file_write_request(data)
                else:
                    if len(data) < 1:
                        continue

                    err = data[0]

                    # 错误响应，清理并退出
                    if err != 0:
                        await self.cleanup()
                        return
                    
                    # 普通响应，唤醒等待的请求
                    for req_id, future in self.pending_requests.items():
                        if not future.done():
                            future.set_result(True)
                            del self.pending_requests[req_id]
                            break
                
            except Exception as e:
                if self.debug_mode:
                    print(f"Error reading from pipe: {e}")
                await asyncio.sleep(0.1)
    
    async def handle_file_write_request(self, data: bytes) -> None:
        """处理文件写入请求"""
        try:
            # 解析数据
            path_len = struct.unpack("<H", data[0:2])[0]
            path = data[2:2+path_len].decode()
            context_len = struct.unpack("<H", data[2+path_len:4+path_len])[0]
            context = data[4+path_len:4+path_len+context_len]
            offset = struct.unpack("<I", data[4+path_len+context_len:8+path_len+context_len])[0]
            
            # 调用文件写入
            self.file_write(path, context, offset)
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error handling file write request: {e}")
    
    async def mkdir(self, path: str) -> bool:
        """创建目录"""
        return await self.fuse_mod_input(0x1, path.encode())
    
    def internal_create(self, path: str, file: VF_File):
        if path in self.file_cache_table:
            return ERR_ALREADY_EXISTS
        
        path_bytes = path.encode()
        flag_bytes = struct.pack("<I", file.getFlag())
        path_len_bytes = struct.pack("<H", len(path_bytes))
        payload = flag_bytes + path_len_bytes + path_bytes
        asyncio.create_task(self.fuse_mod_input(0x02, payload))
        self.file_cache_table[path] = file

        # 如果文件可读，创建数据接收任务
        if file.isAvailableRead():
            asyncio.create_task(self.file_receive_data(path, file))
            asyncio.create_task(self.file_receive_data_append(path, file))
        
        return 0
        
    def create(self, path: str, kwargs: Dict[str, Any] = {}) -> int:
        """创建文件"""
        if path in self.file_cache_table:
            return ERR_ALREADY_EXISTS
        
        file = super().create(path, kwargs)
        if file is None:
            return ERR_NOT_FOUND
        
        return self.internal_create(path, file)
    
    async def rm(self, path: str) -> int:
        """删除文件"""
        if path not in self.file_cache_table:
            return ERR_NOT_FOUND
        
        file = self.file_cache_table[path]
        
        # 取消数据接收任务（在实际实现中需要更复杂的任务管理）
        # 这里简化处理
        
        # 等待文件写入完成（在实际实现中需要跟踪写入任务）
        await asyncio.sleep(0.1)
        
        # 调用文件的删除方法
        await file.rm()
        
        # 通知 FUSE 模块
        await self.fuse_mod_input(0x04, path.encode())
        
        # 从缓存中删除
        del self.file_cache_table[path]
        
        return 0
    
    def file_write(self, path: str, buffer: bytes, offset: int) -> None:
        """文件写入"""
        if path in self.file_cache_table:
            self.file_cache_table[path].write(buffer, offset)
    
    async def file_receive_data(self, path: str, file: VF_File) -> None:
        """接收文件数据，分批处理，使用memoryview优化，发送格式为: path_len(2) path path_len(2) context"""
        try:
            path_bytes = path.encode()
            path_len_bytes = struct.pack("<H", len(path_bytes))
            while self.running and path in self.file_cache_table:
                buffer = await file.read()
                if buffer:
                    mv = memoryview(buffer)
                    total = len(mv)
                    offset = 0
                    chunk_size = PACKET_MAX_SIZE - PACKET_MIN_SIZE - 2
                    first = True
                    while offset < total:
                        chunk = mv[offset:offset+chunk_size]
                        context_len_bytes = struct.pack("<H", len(chunk))
                        payload = path_len_bytes + path_bytes + context_len_bytes + chunk.tobytes()

                        if first:
                            await self.fuse_mod_input(0x05, payload)
                            first = False
                        else:
                            await self.fuse_mod_input(0x06, payload)
                        offset += chunk_size
        except Exception as e:
            if self.debug_mode:
                print(f"Error in file_receive_data for {path}: {e}")
    
    async def file_receive_data_append(self, path: str, file: VF_File) -> None:
        """接收文件追加数据，分批处理，使用memoryview优化，发送格式为: path_len(2) path context_len(2) context"""
        try:
            path_bytes = path.encode()
            path_len_bytes = struct.pack("<H", len(path_bytes))
            while self.running and path in self.file_cache_table:
                buffer = await file.readAppend()
                if buffer:
                    mv = memoryview(buffer)
                    total = len(mv)
                    offset = 0
                    chunk_size = PACKET_MAX_SIZE - PACKET_MIN_SIZE - 2
                    while offset < total:
                        chunk = mv[offset:offset+chunk_size]
                        context_len_bytes = struct.pack("<H", len(chunk))
                        payload = path_len_bytes + path_bytes + context_len_bytes + chunk.tobytes()
                        await self.fuse_mod_input(0x06, payload)
                        offset += chunk_size

        except Exception as e:
            if self.debug_mode:
                print(f"Error in file_receive_data_append for {path}: {e}")
    
    async def run(self) -> None:
        """运行管理器"""

        # 遍历模块树并创建目录
        def mkdir_callback(path: str, module: VF_Module):
            asyncio.create_task(self.mkdir(path))

        def file_create_callback(path: str, file: VF_File):
            self.internal_create(path, file)
        
        self.tree_module(callback=mkdir_callback)
        self.tree_file(callback=file_create_callback)

        # 开始监听
        await self.listen()
    
    async def cleanup(self) -> None:
        """清理资源"""
        self.running = False
        
        # 取消所有待处理的请求
        for future in self.pending_requests.values():
            if not future.done():
                future.set_exception(Exception("Cleanup"))
        
        # 关闭管道
        if self.pipe_in:
            await self.pipe_in.close()
        if self.pipe_out:
            await self.pipe_out.close()
        
        # 终止子进程
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=3)
            except asyncio.TimeoutError:
                self.process.kill()
        
        if self.debug_mode:
            print("Cleanup completed")
        
        # 退出进程
        os._exit(1)
    
    def set_debug_mode(self, enabled: bool) -> None:
        """设置调试模式"""

        def set_debug_mode_callback(path: str, module: VF_Module):
            module.debug_mode = enabled

        self.debug_mode = enabled
        self.tree_module(callback=set_debug_mode_callback)
    