from app.core.security import hash_password, verify_password, create_token, decode_token


def test_hash_and_verify_password():
    password = "secret123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)


def test_create_and_decode_token():
    token = create_token({"sub": "42"})
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "42"


def test_decode_invalid_token_returns_none():
    assert decode_token("invalid.token.here") is None


def test_different_passwords_produce_different_hashes():
    h1 = hash_password("password1")
    h2 = hash_password("password1")
    # bcrypt는 같은 입력도 매번 다른 해시 생성
    assert h1 != h2
    assert verify_password("password1", h1)
    assert verify_password("password1", h2)
