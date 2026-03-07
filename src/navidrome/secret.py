# secret.py

from gi.repository import Secret
import hashlib, secrets, string

BASE_SCHEMA = Secret.Schema.new(
    "com.jeffser.Nocturne.Password",
    Secret.SchemaFlags.NONE,
    {
        "username": Secret.SchemaAttributeType.STRING,
        "base_url": Secret.SchemaAttributeType.STRING
    }
)

def store_password(username:str, base_url:str, password:str):
    attributes = {
        "username": username,
        "base_url": base_url
    }

    Secret.password_store_sync(
        BASE_SCHEMA,
        attributes,
        Secret.COLLECTION_DEFAULT,
        "Nocturne Login",
        password,
        None
    )

def get_hashed_password(username:str, base_url:str) -> tuple:
    # returns salt, hashed password
    attributes = {
        "username": username,
        "base_url": base_url
    }

    password = Secret.password_lookup_sync(
        BASE_SCHEMA,
        attributes,
        None
    )

    salt = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    salted_password = password + salt

    hashed_password = hashlib.md5(salted_password.encode('utf-8')).hexdigest()

    return salt, hashed_password

