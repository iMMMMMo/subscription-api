import argparse
import asyncio
import os
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Create or promote a superuser (admin) account.")
    )

    parser.add_argument(
        "--email",
        default=os.getenv("ADMIN_EMAIL"),
        help="Admin email (or env ADMIN_EMAIL)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("ADMIN_PASSWORD"),
        help=(
            "Admin password for initial creation (or env ADMIN_PASSWORD). "
            "For an existing user, password is only updated with --update-password."
        ),
    )
    parser.add_argument(
        "--full-name",
        default=os.getenv("ADMIN_FULL_NAME"),
        help="Optional full name (or env ADMIN_FULL_NAME)",
    )
    parser.add_argument(
        "--update-password",
        action="store_true",
        help="If the user already exists, also overwrite their password.",
    )

    parser.add_argument(
        "--allow-prod",
        action="store_true",
        help=(
            "Allow running even when APP_ENV is prod-like (prod/production/staging). "
            "Use with care."
        ),
    )

    return parser


async def create_or_promote_superuser(
    *,
    email: str,
    password: str | None,
    full_name: str | None,
    update_password: bool,
) -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            if not password:
                raise ValueError(
                    "Password is required when creating a new admin user. "
                    "Provide --password or set ADMIN_PASSWORD."
                )

            user = User(
                email=email,
                full_name=full_name,
                hashed_password=hash_password(password),
                is_active=True,
                is_superuser=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return f"created_superuser user_id={user.id} email={user.email}"

        changed = False

        if not user.is_superuser:
            user.is_superuser = True
            changed = True

        if not user.is_active:
            user.is_active = True
            changed = True

        if full_name is not None and full_name != user.full_name:
            user.full_name = full_name
            changed = True

        if password and update_password:
            user.hashed_password = hash_password(password)
            changed = True

        if changed:
            await session.commit()
            return f"updated_user user_id={user.id} email={user.email}"

        if password and not update_password:
            return (
                f"no_changes user_id={user.id} email={user.email} "
                "(password provided but ignored; use --update-password to overwrite)"
            )

        return f"no_changes user_id={user.id} email={user.email}"


async def _async_main(argv: list[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    app_env = (settings.app_env or "").strip().lower()
    prod_like_envs = {"prod", "production", "staging"}
    if app_env in prod_like_envs and not args.allow_prod:
        print(
            "error: refusing to create/promote a superuser in APP_ENV="
            f"{settings.app_env!r}. Re-run with --allow-prod to override.",
            file=sys.stderr,
        )
        return 3

    if not args.email:
        parser.error("--email is required (or set ADMIN_EMAIL)")

    try:
        message = await create_or_promote_superuser(
            email=args.email,
            password=args.password,
            full_name=args.full_name,
            update_password=args.update_password,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(message)
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_async_main(sys.argv[1:])))


if __name__ == "__main__":
    main()
