import os
import re
import stat
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timezone as dt_timezone

from cryptography import x509
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtensionOID, ExtendedKeyUsageOID, ObjectIdentifier
from django.conf import settings
from django.utils import timezone

from .exceptions import MdfeConfigurationError, MdfeError


CNPJ_OTHER_NAME_OID = ObjectIdentifier("2.16.76.1.3.3")


@dataclass
class CertificateMaterial:
    private_key: object
    certificate: x509.Certificate
    additional_certificates: tuple
    cnpj: str


def _fernet():
    key = settings.MDFE_ENCRYPTION_KEY
    if not key:
        raise MdfeConfigurationError(
            "Defina MDFE_ENCRYPTION_KEY antes de cadastrar o certificado.", code="encryption_key_missing"
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise MdfeConfigurationError(
            "MDFE_ENCRYPTION_KEY não é uma chave Fernet válida.", code="encryption_key_invalid"
        ) from exc


def encrypt_secret(value):
    return _fernet().encrypt(bytes(value))


def decrypt_secret(value):
    try:
        return _fernet().decrypt(bytes(value))
    except InvalidToken as exc:
        raise MdfeConfigurationError(
            "Não foi possível descriptografar a configuração fiscal.", code="encrypted_data_invalid"
        ) from exc


def _decode_other_name(value):
    if not value:
        return ""
    # OtherName vem codificado em DER. Remove tag e comprimento de strings ASN.1 usuais.
    data = bytes(value)
    if len(data) >= 2 and data[0] in (0x0C, 0x13, 0x16, 0x1E):
        length_byte = data[1]
        offset = 2
        if length_byte & 0x80:
            count = length_byte & 0x7F
            if len(data) < 2 + count:
                return ""
            length = int.from_bytes(data[2:2 + count], "big")
            offset = 2 + count
        else:
            length = length_byte
        data = data[offset:offset + length]
        if data and data[0] == 0 and len(data) % 2 == 0:
            try:
                return data.decode("utf-16-be")
            except UnicodeDecodeError:
                pass
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return ""


def certificate_cnpj(certificate):
    try:
        san = certificate.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value
    except x509.ExtensionNotFound:
        return ""
    for name in san:
        if isinstance(name, x509.OtherName) and name.type_id == CNPJ_OTHER_NAME_OID:
            text = _decode_other_name(name.value).upper()
            match = re.search(r"[A-Z0-9]{12}[0-9]{2}", re.sub(r"[^A-Z0-9]", "", text))
            if match:
                return match.group(0)
    return ""


def load_pkcs12(data, password, *, expected_cnpj=None, check_validity=True):
    try:
        private_key, certificate, additional = pkcs12.load_key_and_certificates(
            bytes(data), str(password).encode("utf-8") if password else None
        )
    except (ValueError, TypeError) as exc:
        raise MdfeError("Certificado A1 inválido ou senha incorreta.", code="invalid_certificate") from exc
    if private_key is None or certificate is None:
        raise MdfeError("O arquivo não contém certificado e chave privada.", code="invalid_certificate")
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise MdfeError("A chave privada do certificado não permite assinatura RSA.", code="invalid_certificate")

    now = timezone.now().astimezone(dt_timezone.utc)
    not_before = certificate.not_valid_before_utc
    not_after = certificate.not_valid_after_utc
    if check_validity and (now < not_before or now > not_after):
        raise MdfeError("O certificado digital está fora do período de validade.", code="expired_certificate")

    try:
        usage = certificate.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE).value
        if not (usage.digital_signature or usage.content_commitment):
            raise MdfeError("O certificado não permite assinatura digital.", code="invalid_certificate_usage")
    except x509.ExtensionNotFound:
        pass
    try:
        extended = certificate.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE).value
        if ExtendedKeyUsageOID.CLIENT_AUTH not in extended:
            raise MdfeError("O certificado não permite autenticação TLS de cliente.", code="invalid_certificate_usage")
    except x509.ExtensionNotFound:
        pass

    cnpj = certificate_cnpj(certificate)
    if not cnpj:
        raise MdfeError(
            "O certificado não contém CNPJ no otherName ICP-Brasil (OID 2.16.76.1.3.3).",
            code="certificate_cnpj_missing",
        )
    if expected_cnpj and cnpj[:8] != expected_cnpj[:8]:
        raise MdfeError(
            "O CNPJ-base do certificado não corresponde à transportadora.", code="certificate_cnpj_mismatch"
        )
    return CertificateMaterial(private_key, certificate, tuple(additional or ()), cnpj)


def load_configuration_material(configuration):
    pfx = decrypt_secret(configuration.certificado_criptografado)
    password = decrypt_secret(configuration.senha_criptografada).decode("utf-8")
    return load_pkcs12(pfx, password, expected_cnpj=configuration.cnpj)


def certificate_metadata(material):
    return {
        "cnpj": material.cnpj,
        "fingerprint": material.certificate.fingerprint(hashes.SHA256()).hex().upper(),
        "valid_from": material.certificate.not_valid_before_utc,
        "valid_until": material.certificate.not_valid_after_utc,
    }


@contextmanager
def tls_certificate_files(material):
    with tempfile.TemporaryDirectory(prefix="mdfe-tls-") as directory:
        os.chmod(directory, stat.S_IRWXU)
        cert_path = os.path.join(directory, "client-cert.pem")
        key_path = os.path.join(directory, "client-key.pem")
        certificate_chain = material.certificate.public_bytes(serialization.Encoding.PEM)
        certificate_chain += b"".join(
            certificate.public_bytes(serialization.Encoding.PEM)
            for certificate in material.additional_certificates
        )
        key = material.private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        for path, value in ((cert_path, certificate_chain), (key_path, key)):
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
            with os.fdopen(descriptor, "wb") as file:
                file.write(value)
        try:
            yield cert_path, key_path
        finally:
            key = b""
