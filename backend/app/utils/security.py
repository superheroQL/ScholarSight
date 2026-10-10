from passlib.context import CryptContext

# bcrypt_sha256 先对密码做 SHA-256，避免 bcrypt 的 72 字节限制。
# 保留 bcrypt 以兼容数据库中已经生成的旧密码哈希。
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")


def get_hash_password(password: str) -> str:
    """
    对密码进行哈希处理
    :param password: 明文密码
    :return: 哈希后的密码
    """
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    """
    验证密码是否正确
    :param password: 明文密码
    :param hashed_password: 哈希后的密码
    :return: 验证结果 返回 True 表示密码正确，False 表示密码错误
    """
    return pwd_context.verify(password, hashed_password)