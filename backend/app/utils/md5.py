import hashlib
from fastapi import UploadFile


async def get_md5(file: UploadFile) -> str:
    md5 = hashlib.md5()

    while chunk := await file.read(1024 * 1024):  # 每次读取 1MB
        md5.update(chunk)

    # 计算完后把文件指针恢复到开头
    await file.seek(0)

    return md5.hexdigest()