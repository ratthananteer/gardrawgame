from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
import datetime

# เตรียมโฟลเดอร์เก็บไฟล์ (ถ้ายังไม่มี)
import os
os.makedirs('certs', exist_ok=True)

# สร้าง Private Key
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=4096,
    backend=default_backend()
)

# บันทึก Private Key
with open("certs/key.pem", "wb") as key_file:
    key_file.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))

# สร้าง Self-Signed Certificate
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, "TH"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Bangkok"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MyApp"),
    x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
])

cert = x509.CertificateBuilder().subject_name(
    subject
).issuer_name(
    issuer
).public_key(
    private_key.public_key()
).serial_number(
    x509.random_serial_number()
).not_valid_before(
    datetime.datetime.utcnow()
).not_valid_after(
    datetime.datetime.utcnow() + datetime.timedelta(days=365)
).add_extension(
    x509.BasicConstraints(ca=True, path_length=None),
    critical=True,
).sign(private_key, hashes.SHA256(), default_backend())

# บันทึก Certificate
with open("certs/cert.pem", "wb") as cert_file:
    cert_file.write(cert.public_bytes(serialization.Encoding.PEM))

print("สร้างไฟล์สำเร็จ:")
print("- Private Key: certs/key.pem")
print("- Certificate: certs/cert.pem")