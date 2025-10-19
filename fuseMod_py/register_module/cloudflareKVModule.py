from typing import Dict, Any
import aiohttp
import asyncio
import time

from ..VF_File import VF_File
from ..VF_Module import VF_Module

async def put_kv_value(account_id, namespace_id, api_key, key, value):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/values/{key}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "text/plain",
    }
    
    try:
        async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, data=value) as response:
                    await response.text()

    except aiohttp.ClientError as e:
        pass

async def get_kv_value(account_id, namespace_id, api_key, key):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/values/{key}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "text/plain",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                text = await response.text()
        return text
    except aiohttp.ClientError as e:
        return None

class CloudFlareKVFile(VF_File):
    def __init__(self, flag, argv) -> None:
        super().__init__(flag)
        self.argv = argv
        self.hasInit = False
    
    def write(self, buffer: bytes, offset: int) -> None:
        self.content = buffer
        asyncio.create_task(
            put_kv_value(
            self.argv["account_id"],
            self.argv["namespace_id"],
            self.argv["api_key"],
            self.argv["key"],
            buffer
        ))
        
    async def read(self):
        
        while True:
            if self.hasInit == False:
                self.hasInit = True
            else:
                await asyncio.sleep(self.argv["updateTimeMin"] * 60)
            
            res = await get_kv_value(
                self.argv["account_id"],
                self.argv["namespace_id"],
                self.argv["api_key"],
                self.argv["key"],
            )
            
            if res == None:
                continue
            else:
                return res.encode()

class CloudFlareKVInstance(VF_Module):
    def __init__(self, global_table: Dict, enableDebug=False) -> None:
        super().__init__(global_table, enableDebug)
        self.init_from_config()
        
    def init_from_config(self):
        config = self.read_config("cloudflareKV")
        for instance in config["instances"]:
            self.register_file(instance["name"], instance["argv"])
    
    def create_file(self, name: str, kwargs: Dict[str, Any]) -> "VF_File | None":
        return CloudFlareKVFile(VF_File.FLAG_READ | VF_File.FLAG_WRITE | VF_File.FLAG_COPY_ON_WRITE, kwargs)


class CloudFlareKVModule(VF_Module):
    def __init__(self, global_table: Dict, enableDebug=False) -> None:
        super().__init__(global_table, enableDebug)
        self.register_module("instance", CloudFlareKVInstance(global_table))