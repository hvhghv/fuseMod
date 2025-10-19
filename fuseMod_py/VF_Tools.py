import crcmod
from typing import Optional, Tuple

# CRC16-CCITT 计算函数
crc16_ccitt = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0, xorOut=0)

def path_parse(path: str) -> Optional[Tuple[str, str]]:
    """
    解析路径，返回 [name, subPath]
    
    参数:
        path: 要解析的路径，必须以"/"开头
        
    返回:
        成功时返回 (name, subPath) 元组，失败返回 None
    """
    if not path.startswith('/'):
        return None
    
    # 移除开头的斜杠并分割路径
    parts = path[1:].split('/', 1)
    
    if len(parts) == 1:
        # 只有一级路径
        return parts[0], '/'
    else:
        # 多级路径
        return parts[0], '/' + parts[1]