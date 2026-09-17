import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole


class AuthenticationError(Exception):
    """Raised when credentials or account state cannot be accepted."""


class AccountError(Exception):
    """Raised when account data violates a domain rule."""


class PasswordHasher:
    """Encapsulates password hashing and verification behind one reusable class."""

    algorithm = "pbkdf2_sha256"
    iterations = 310_000

    @classmethod
    def hash(cls, password: str) -> str:
        if len(password) < 8:
            raise AccountError("Password must contain at least 8 characters")
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, cls.iterations)
        return f"{cls.algorithm}${cls.iterations}${salt.hex()}${digest.hex()}"

    @classmethod
    def verify(cls, password: str, encoded: str) -> bool:
        try:
            algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
            if algorithm != cls.algorithm:
                return False
            digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
            return hmac.compare_digest(digest.hex(), digest_hex)
        except (ValueError, TypeError):
            return False


@dataclass(frozen=True)
class AccountSummary:
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool


class AccountService:
    """Owns account creation and profile-management operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_account(self, email: str, full_name: str, password: str, role: str = UserRole.viewer.value) -> User:
        normalized_email = email.strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise AccountError("Enter a valid email address")
        if role not in {item.value for item in UserRole}:
            raise AccountError("Unsupported account role")
        account = User(email=normalized_email, full_name=full_name.strip(), password_hash=PasswordHasher.hash(password), role=role)
        self.session.add(account)
        try:
            await self.session.commit()
            await self.session.refresh(account)
            return account
        except IntegrityError as error:
            await self.session.rollback()
            raise AccountError("An account with that email already exists") from error

    async def get_account(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def update_profile(self, user: User, full_name: str, password: str | None = None) -> User:
        if not full_name.strip():
            raise AccountError("Full name cannot be empty")
        user.full_name = full_name.strip()
        if password:
            user.password_hash = PasswordHasher.hash(password)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def list_accounts(self) -> list[User]:
        return list((await self.session.scalars(select(User).order_by(User.created_at))).all())


class AuthenticationService:
    """Authenticates accounts and records successful login activity."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.session.scalar(select(User).where(User.email == email.strip().lower()))
        if not user or not user.is_active or not PasswordHasher.verify(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        user.last_login_at = datetime.now(timezone.utc)
        await self.session.commit()
        return user
