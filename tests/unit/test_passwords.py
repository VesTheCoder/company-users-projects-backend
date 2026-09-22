from app.auth.passwords import PasswordHasherService


async def test_argon2_profile_verification_and_rehash():
    service = PasswordHasherService()
    encoded = await service.hash("a test password")
    assert "$argon2id$v=19$m=65536,t=3,p=4$" in encoded
    assert await service.verify("a test password", encoded)
    assert not await service.verify("wrong", encoded)
    assert not service.needs_rehash(encoded)
