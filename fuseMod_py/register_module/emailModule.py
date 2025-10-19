import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Dict, Any

import asyncio
from ..VF_File import VF_File
from ..VF_Module import VF_Module

class SendEmailDecodeError(Exception):
    pass

async def send_email(host, port, account, password, sender, sender_email, receiver, receiver_email, subject, context, ssl=False, tls=False):
    """
    发送电子邮件函数
    
    参数:
    host: SMTP服务器主机地址
    port: SMTP服务器端口
    account: 登录账号
    password: 登录密码
    sender: 发件人邮箱
    receiver: 收件人邮箱（可以是字符串或列表）
    subject: 邮件主题
    context: 邮件正文内容
    ssl: 是否使用SSL加密（默认False）
    tls: 是否使用TLS加密（默认False）
    """
    
    # 创建邮件内容对象
    def sync_code(host, port, account, password, sender, sender_email, receiver, receiver_email, subject, context, ssl, tls):
        while (1):
            try:
                context = context.decode("utf-8")
                break
            except UnicodeDecodeError:
                pass

            try: 
                context = context.decode("gbk")
                break
            except UnicodeDecodeError:
                pass

            raise SendEmailDecodeError()

        message = MIMEText(context, 'plain', 'utf-8')
        message['From'] = formataddr([sender,sender_email]) # type: ignore
        message['To'] = formataddr([receiver,receiver])# type: ignore
        message['Subject'] = subject # type: ignore
        
        try:
            # 使用SSL加密连接
            if ssl:
                server = smtplib.SMTP_SSL(host, port)
            else:
                server = smtplib.SMTP(host, port)

                # 启用TLS加密（如果不需要SSL但需要TLS）
                if tls:
                    server.starttls()
            
            # 登录SMTP服务器
            server.login(account, password)
            # 发送邮件
            server.sendmail(sender_email, receiver_email, message.as_string())
            # 关闭连接
            server.quit()
            return True
        except Exception as e:
            return False
        
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, sync_code, host, port, account, password, sender, sender_email, receiver, receiver_email, subject, context, ssl, tls)

class EmailFile(VF_File):
    def __init__(self, flag, kwargs) -> None:
        super().__init__(flag)
        self.host = kwargs["host"]
        self.port = kwargs["port"]
        self.account = kwargs["account"]
        self.password = kwargs["password"]
        self.sender = kwargs["sender"]
        self.sender_email = kwargs["sender_email"]
        self.receiver = kwargs["receiver"]
        self.receiver_email = kwargs["receiver_email"]
        self.subject = kwargs["subject"]
        self.ssl = kwargs["ssl"]
        self.tls = kwargs["tls"]

    def write(self, buffer: bytes, offset: int) -> None:
        try:
            asyncio.create_task(send_email(self.host, self.port, self.account, self.password, self.sender, self.sender_email, self.receiver, self.receiver_email, self.subject, buffer, self.ssl, self.tls))
        except:
            pass
    

class EmailModule(VF_Module):
    def __init__(self, global_table: Dict) -> None:
        super().__init__(global_table)
        self.init_email_form_config()

    def init_email_form_config(self):
        config = self.read_config("email")
        for instance in config["instances"]:
            self.register_file(instance["name"], instance["argv"])

    def create_file(self, name: str, kwargs: Dict[str, Any]) -> VF_File:
        return EmailFile(VF_File.FLAG_WRITE, kwargs)
    

