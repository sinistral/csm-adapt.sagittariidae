
import json
import urllib2

from jose import jwt

# Unfortunately we have to depend on multiple crypto libraries.  PyCrypto
# provides the lower-level functions to work with DER-encoded keys, and JOSE
# supports its types for RSA keys (we could also have used Pycryptodome as a
# drop-in replacement for PyCrypto).
#
# But, PyCrypto doesn't provide any certificate management functions. For that
# we turn to PyOpenSSL, which is unfortunately not a pure Python solution, but
# wraps the system's OpenSSL library.  As long as we deploy using
# {conda,virtualenv} virtual environments, we shouldn't run into version
# conflicts between the system OpenSSL and the OpenSSL library required by the
# PyOpenSSL module.
from Crypto      import PublicKey
from Crypto.Util import asn1
from OpenSSL     import crypto


class JWTDecoder(object):
    """
    A [JWT](https://jwt.io) decoder that will decode and validate a token using
    one of the keys with which it has been initialised.
    """

    def __init__(self, keys):
        """
        Initialise a new instance of the decoder.  `keys` is a dict that maps
        key IDs to (RSA) key instances.
        """
        self.keys = keys.copy()

    def decode(self, token, key_id, issuer, audience):
        """
        Decode `token` using the key identified by `key_id`, which must be
        present in the dict with which the instance was initialised.
        """
        assert key_id in self.keys.keys()
        return jwt.decode(
            token, self.keys[key_id], issuer=issuer, audience=audience)


class X509JWTDecoder(JWTDecoder):
    """
    A [JWT](https://jwt.io) decoder that will decode and valdiate a token using
    one of the keys that it has extracted from the collection of (PEM-encoded)
    X.509 certificates with which it has been initialised.
    """
    def __init__(self, certs):

        def cert_to_key(dictentry):
            # Alias tuple components for readability
            key_id = dictentry[0]
            pem_cert = dictentry[1]

            # Convert the PEM-encoded certificates into DER, from which we can
            # get the DER-encoded public key.  This we can use to create a
            # PyCrypto RSA key.
            #
            # PyOpenSSL does provide RSA key implementations, but these are not
            # compatible with JOSE, which supports only PyCrypto and
            # Pycryptodome, neither of which provides mechanisms for working
            # with X509 certificates.
            #
            # So we take this circuitous route of converting betweena
            # serialisation formats before we can get to a usable key object:
            #   PEM cert -> DER/ASN1 cert -> DER/ASN1 public key -> Pycrypto RSAKey

            # FIXME: We should validate that we're pulling the key out of a
            # valid, current certificate.

            pub_key = crypto.load_certificate(
                crypto.FILETYPE_PEM, pem_cert).get_pubkey()
            key_der = crypto.dump_publickey(crypto.FILETYPE_ASN1, pub_key)

            return (key_id, PublicKey.RSA.importKey(key_der))

        super(X509JWTDecoder, self).__init__(dict(map(cert_to_key, certs.items())))


class FirebaseJWTDecoder(X509JWTDecoder):

    FIREBASE_PROJECT='sagittariidae-4e8fd'
    FIREBASE_JWT_ISSUER = 'https://securetoken.google.com/' + FIREBASE_PROJECT
    FIREBASE_JWT_CERTS_URI = 'https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com'
    FIREBASE_JWT_CERTS = json.loads(urllib2.urlopen(FIREBASE_JWT_CERTS_URI).read())

    def __init__(self):
        super(FirebaseJWTDecoder, self).__init__(self.FIREBASE_JWT_CERTS)

    def decode(self, token):
        # Get the token headers without any validation.  We do this first to
        # retrieve the ID of the key that was used to sign the token.
        hdr = jwt.get_unverified_headers(token)

        alg = hdr['alg']
        assert hdr['alg'] == 'RS256' # [1]

        kid = hdr['kid']
        assert kid is not None

        # Decode the token, and validate its claims; in particular ensure that
        # the signature can be verified using the designated key.
        data = super(FirebaseJWTDecoder, self).decode(
            token, kid, self.FIREBASE_JWT_ISSUER, self.FIREBASE_PROJECT)

        assert data['sub'] == data['user_id'] # [1]

        return \
            {'uid'           : data['user_id'],
             'authenticator' : data['firebase']['sign_in_provider']}

# [1] https://firebase.google.com/docs/auth/server/verify-id-tokens#verify_id_tokens_using_a_third-party_jwt_library
