from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2
from Crypto import Random
import base64

SALT_SIZE = 32
KEY_SIZE = 32


def func_encrypt(key, data):
    salt = get_random_bytes(SALT_SIZE)
    master_key = PBKDF2(key[:KEY_SIZE], salt, dkLen=32)
    data_to_encrypt = data
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(master_key, AES.MODE_CBC, iv)
    padded_data = pad(data_to_encrypt.encode('utf-8'), AES.block_size)
    return base64.b64encode(salt + iv + cipher.encrypt(padded_data)).decode('utf-8')


def func_decrypt(key, enc_data):
    salty_data = base64.b64decode(enc_data)
    salt = salty_data[0:SALT_SIZE]
    unsalted_cipher_text = salty_data[SALT_SIZE:]
    iv = unsalted_cipher_text[:AES.block_size]
    master_key = PBKDF2(key[:KEY_SIZE], salt, dkLen=32)
    cipher = AES.new(master_key, AES.MODE_CBC, iv)
    padded_plaintext = cipher.decrypt(unsalted_cipher_text[AES.block_size:])
    plaintext = unpad(padded_plaintext, AES.block_size)
    return plaintext.decode('utf-8')