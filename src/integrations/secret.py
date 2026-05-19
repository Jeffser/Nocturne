# secret.py

from gi.repository import Secret
import hashlib, secrets, string
from ..constants import FALLBACK_PASSWORD_PATH

BASE_SCHEMA = Secret.Schema.new(
    "com.jeffser.Nocturne.Password",
    Secret.SchemaFlags.NONE,
    {
        "type": Secret.SchemaAttributeType.STRING
    }
)

def store_password(password:str, schema_type:str="password"):
    try:
        attributes = {"type": schema_type}

        Secret.password_store_sync(
            BASE_SCHEMA,
            attributes,
            Secret.COLLECTION_DEFAULT,
            "Nocturne Login",
            password,
            None
        )
    except Exception as e:
        with open(FALLBACK_PASSWORD_PATH, 'w') as f:
            f.write(password)

def get_plain_password(schema_type:str="password") -> str:
    # returns plain password
    try:
        attributes = {"type": schema_type}

        return Secret.password_lookup_sync(
            BASE_SCHEMA,
            attributes,
            None
        )
    except Exception as e:
        with open(FALLBACK_PASSWORD_PATH, 'r') as f:
            return f.read()
    return ""

def get_hashed_password(schema_type:str="password") -> tuple:
    # returns salt, hashed password
    salt = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    salted_password = get_plain_password(schema_type) + salt

    hashed_password = hashlib.sha256(salted_password.encode('utf-8')).hexdigest()

    return salt, hashed_password

def remove_password(schema_type:str="password", callback:callable=lambda:None):
    Secret.password_clear(
        BASE_SCHEMA,
        {"type": schema_type},
        None,
        callback,
        None
    )
