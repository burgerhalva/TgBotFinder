import json
import string
import asyncio
import argparse
import sys
import urllib.request
from pathlib import Path
from typing import Iterable

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    AccessTokenInvalidError,
    PhoneNumberInvalidError,
    PhonePasswordFloodError,
    PasswordHashInvalidError,
)
from telethon.tl import types
from telethon.tl.functions.contacts import SearchRequest


DEFAULT_ALPHABET = string.ascii_lowercase
DEFAULT_SESSION_PATH = Path.home() / ".tgbotfinder" / "user.session"
DEFAULT_OUTPUT_PATH = Path.home() / ".tgbotfinder" / "result.json"
DEFAULT_SEARCH_LIMIT = 999
DEFAULT_API_ID = 16623
DEFAULT_API_HASH = "8c9dbfe58437d1739540f5d53c72ae4b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Search Telegram bots and channels using word mutations"
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--word",
        help="Main word for fuzzy search",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help="Path to JSON results file.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between queries in seconds.",
    )
    parser.add_argument(
        "--api-id",
        type=int,
        default=DEFAULT_API_ID,
        help="Telegram API ID. Overrides default.",
    )
    parser.add_argument(
        "--api-hash",
        default=DEFAULT_API_HASH,
        help="Telegram API hash. Overrides default.",
    )
    parser.add_argument(
        "--logout",
        action="store_true",
        help="Delete session file",
    )
    args = parser.parse_args()
    if args.logout:
        if len(sys.argv[1:]) != 1:
            parser.error("--logout must be used alone.")
        return args

    if not args.word:
        parser.error("the following arguments are required: --word")

    return args


def remove_session_file(session_path: Path) -> bool:
    try:
        session_path.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        print(f"[!] Could not remove session file: {session_path}")
        print(f"[!] {exc}")
        print("[!] Delete this file manually and run program again.")
        return False

    return True


def build_queries(word: str, alphabet: str = DEFAULT_ALPHABET) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()

    def add(candidate: str) -> None:
        if candidate not in seen:
            seen.add(candidate)
            queries.append(candidate)

    # mutations
    
    add(f"{word}bot")
    add(f"{word}_bot")

    for symbol in alphabet:
        add(f"{word}_{symbol}")

    for symbol in alphabet:
        add(f"{symbol}_{word}")

    for symbol in alphabet:
        add(f"{word}_{symbol}_bot")

    for symbol in alphabet:
        add(f"{word}_{symbol}bot")

    return queries


def entity_type(entity: types.TypePeer) -> str:
    if isinstance(entity, types.User):
        return "bot" if entity.bot else "user"
    if isinstance(entity, types.Channel):
        return "megagroup" if entity.megagroup else "channel"
    if isinstance(entity, types.Chat):
        return "chat"
    return type(entity).__name__


def entity_to_dict(entity: types.TypePeer, query: str, source_word: str) -> dict:
    username = getattr(entity, "username", None)
    title = getattr(entity, "title", None)
    if isinstance(entity, types.User):
        name_parts = [entity.first_name or "", entity.last_name or ""]
        title = " ".join(part for part in name_parts if part).strip() or None

    return {
        "id": getattr(entity, "id", None),
        "type": entity_type(entity),
        "title": title,
        "username": username,
        "username_link": f"https://t.me/{username}" if username else None,
        "query": query,
        "source_word": source_word,
    }


def should_keep_entity(entity: types.TypePeer) -> bool:
    if isinstance(entity, types.User):
        return bool(entity.bot)
    if isinstance(entity, types.Channel):
        return True
    return False


def format_entity_line(item: dict) -> str:
    title = item.get("title") or "-"
    username = item.get("username")
    link = item.get("username_link") or "-"

    if username:
        return f"- {title} | @{username} | {link}"
    return f"- {title} | no_username | {link}"


def print_section(title: str, items: list[dict]) -> None:
    print(f"\n{title}")
    print("=" * len(title))
    if not items:
        print("- nothing found")
        return

    for item in sorted(
        items,
        key=lambda value: (
            value.get("username") or "",
            value.get("title") or "",
            value.get("id") or 0,
        ),
    ):
        print(format_entity_line(item))


def print_pretty_results(results: list[dict]) -> None:
    bots = [item for item in results if item["type"] == "bot"]
    channels = [
        item for item in results if item["type"] in {"channel", "megagroup"}
    ]

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"Total unique entities: {len(results)}")
    print(f"Bots: {len(bots)}")
    print(f"Channels/groups: {len(channels)}")

    print_section("BOTS", bots)
    print_section("CHANNELS AND GROUPS", channels)


def iter_entities(result: types.contacts.Found) -> Iterable[types.TypePeer]:
    for entity in result.users:
        yield entity
    for entity in result.chats:
        yield entity


def build_client(args: argparse.Namespace) -> TelegramClient:
    DEFAULT_SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    return TelegramClient(
        str(DEFAULT_SESSION_PATH),
        args.api_id,
        args.api_hash,
    )


async def check_telegram_access() -> None:
    try:
        request = urllib.request.Request(
            "https://telegram.org/",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        await asyncio.to_thread(urllib.request.urlopen, request, timeout=10)
    except Exception as exc:
        print("[!] No HTTP access to telegram.org. Telegram may be blocked, filtered, or unavailable.")
        exit(1)


async def ensure_working_session(client: TelegramClient) -> bool:
    if not await client.is_user_authorized():
        raise RuntimeError("Telegram authorization did not complete successfully.")

    me = await client.get_me()
    if getattr(me, "bot", False):
        print("[!] Bot token is not supported. Log in with phone number.")
        return False
    print("[+] Telegram session is authorized.")
    return True


async def run_search(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    session_path = DEFAULT_SESSION_PATH
    word = args.word.strip()

    results: list[dict] = []
    seen_entities: set[tuple[int | None, str]] = set()
    remove_bot_session = False

    await check_telegram_access()

    client = build_client(args)
    try:
        await client.start()
    except PasswordHashInvalidError:
        print("[!] Invalid Telegram 2FA password after 3 attempts.")
        print("[!] Run the script again and enter the correct password.")
        try:
            await client.disconnect()
        except Exception:
            pass
        return 1
    except PhonePasswordFloodError:
        print("[!] Phone password flood error. Telegram is temporarily unavailable.")
        print("[!] Run the script again later.")
        try:
            await client.disconnect()
        except Exception:
            pass
        return 1
    except FloodWaitError:
        print("[!] Flood wait error. Telegram is temporarily unavailable.")
        print("[!] Run the script again later.")
        try:
            await client.disconnect()
        except Exception:
            pass
        return 1
    except AccessTokenInvalidError:
        print("[!] Do not use bot token. Use phone number instead.")
        return 1
    except PhoneNumberInvalidError:
        print("[!] Invalid phone number.")
        return 1
    except RuntimeError as exc:
        if "sign-in attempts failed" in str(exc):
            print("[!] Telegram sign-in failed after 3 attempts.")
            print("[!] Run the script again and enter the correct Telegram code/password.")
            try:
                await client.disconnect()
            except Exception:
                pass
            return 1

        raise

    try:
        if not await ensure_working_session(client):
            remove_bot_session = True
        else:
            queries = build_queries(word)

            print(f"[+] Word: {word} ({len(queries)} queries)")

            for query in queries:
                print(f"    -> searching: {query}")
                try:
                    response = await client(
                        SearchRequest(q=query, limit=DEFAULT_SEARCH_LIMIT)
                    )
                except Exception as exc:
                    print(f"       ! failed: {exc}")
                    await asyncio.sleep(args.delay)
                    continue

                query_hits = 0
                for entity in iter_entities(response):
                    if not should_keep_entity(entity):
                        continue

                    item = entity_to_dict(entity, query=query, source_word=word)
                    dedupe_key = (item["id"], item["type"])
                    if dedupe_key in seen_entities:
                        continue

                    seen_entities.add(dedupe_key)
                    results.append(item)
                    query_hits += 1

                print(f"       found new entities: {query_hits}")
                await asyncio.sleep(args.delay)
    finally:
        await client.disconnect()

    if remove_bot_session:
        remove_session_file(session_path)
        return 1

    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print_pretty_results(results)
    print(f"\n[+] Saved {len(results)} unique entities to {output_path}")
    return 0


def main() -> None:
    args = parse_args()
    if args.logout:
        raise SystemExit(0 if remove_session_file(DEFAULT_SESSION_PATH) else 1)

    raise SystemExit(asyncio.run(run_search(args)))


if __name__ == "__main__":
    main()
