from fastapi.security import OAuth2AuthorizationCodeBearer
from keycloak import KeycloakOpenID  # pip require python-keycloak
from .config import settings
from fastapi import Security, HTTPException, status
from pydantic import Json

# This is just for fastapi docs
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=settings.auth.authorization_url,  # https://sso.example.com/auth/
    tokenUrl=settings.auth.token_url,  # https://sso.example.com/auth/realms/example-realm/protocol/openid-connect/token
)

# This actually does the auth checks
keycloak_openid = KeycloakOpenID(
    server_url=settings.auth.server_url,  # https://sso.example.com/auth/
    client_id=settings.auth.client_id,  # backend-client-id
    realm_name=settings.auth.realm,  # example-realm
    client_secret_key=settings.auth.client_secret,  # your backend client secret
    verify=True
)


async def get_idp_public_key():
    return (
        "-----BEGIN PUBLIC KEY-----\n"
        f"{keycloak_openid.public_key()}"
        "\n-----END PUBLIC KEY-----"
    )


async def get_auth(token: str = Security(oauth2_scheme)) -> Json:
    try:
        return keycloak_openid.decode_token(
            token,
            key=await get_idp_public_key(),
            options={
                "verify_signature": True,
                "verify_aud": True,
                "exp": True
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),  # "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )