
import pytest

from Crypto  import PublicKey
from OpenSSL import crypto
from jose    import jwt
from time    import gmtime, time

import app.authn as authn


@pytest.fixture(scope='function')
def pkey():
    pkey = crypto.PKey()
    pkey.generate_key(crypto.TYPE_RSA, 1024)
    return {'key': pkey,
            'der': crypto.dump_privatekey(crypto.FILETYPE_ASN1, pkey)}


@pytest.fixture(scope='function')
def cert(pkey):
    rsa_key = pkey['key']
    # Mutation, urgh!  Why no builder, OpenSSL?!
    cert = crypto.X509()
    # Who/what does the certificate identify?
    subj    = cert.get_subject()
    subj.C  = 'US'                       # country
    subj.ST = 'CO'                       # state/province
    subj.O  = 'Colorado School of Mines' # organisation
    subj.OU = 'ADAPT'                    # organisational unit
    # Certificate metadata
    cert.set_serial_number(1)
    cert.gmtime_adj_notBefore(int(time()) - 5)
    cert.gmtime_adj_notAfter(int(time()) + 5)
    cert.set_issuer(subj)                # self-signed cert
    cert.set_pubkey(rsa_key)
    cert.sign(rsa_key, 'sha1')

    return cert


@pytest.fixture(scope='function')
def decoder(cert):
    return authn.X509JWTDecoder(
        {'cert-0': crypto.dump_certificate(crypto.FILETYPE_PEM, cert)})


def make_token(claims, key):
    return jwt.encode(claims, key, algorithm='RS256')


def test_decode_valid(decoder, pkey, cert):
    claims = {'iss': 'ADAPT', 'exp': int(time()) + 5}
    token = make_token(claims, pkey['der'])
    assert claims == decoder.decode(token, 'cert-0', 'ADAPT', 'test')


def test_decode_expired_token(pkey, cert):
    cert.gmtime_adj_notAfter(int(time()) - 5)
    decoder = authn.X509JWTDecoder(
        {'cert-0': crypto.dump_certificate(crypto.FILETYPE_PEM, cert)})
    claims = {'iss': 'ADAPT', 'exp': int(time()) - 5}
    token = make_token(claims, pkey['der'])
    with pytest.raises(jwt.ExpiredSignatureError):
        decoder.decode(token, 'cert-0', 'ADAPT', 'test')


def test_decode_token_w_invalid_issuer(decoder, pkey, cert):
    claims = {'iss': 'ADAPT'}
    token = make_token(claims, pkey['der'])
    with pytest.raises(jwt.JWTClaimsError) as ex:
        decoder.decode(token, 'cert-0', 'not-ADAPT', 'test')
    assert 'Invalid issuer' in str(ex.value)


def test_decode_token_w_invalid_key(decoder, pkey, cert):
    claims = {'iss': 'ADAPT'}
    token = make_token(claims, pkey['der'])
    with pytest.raises(AssertionError) as ex:
        decoder.decode(token, 'cert-1', 'not-ADAPT', 'test')
    assert "assert 'cert-1' in ['cert-0']" in str(ex.value)
