import argparse
import json
import socket
import time
from typing import Any, Dict

import keyboard


# Network defaults (override with CLI flags if needed).
DEFAULT_RPI_IP = "172.20.10.2"
DEFAULT_RPI_PORT = 5005
DEFAULT_COUNTDOWN_HOST = "127.0.0.1"
DEFAULT_COUNTDOWN_PORT = 5005

# Hero name -> countdown timer id mapping.
# This is the mapping location you can edit later.
HERO_TIMER_MAP = {
    "蓋倫": 1,
    "安妮": 2,
    "好運姐": 3,
    "阿姆姆": 4,
    "雷歐娜": 5,
    "墨菲特": 6,
    "馬爾札哈": 7,
    "艾希": 8,
    "沃維克": 9,
    "索娜": 10,
}


def _get_field(payload: Dict[str, Any], key: str, default: str = "") -> str:
    """Read field from top-level first, then payload['message']."""
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()

    message = payload.get("message")
    if isinstance(message, dict):
        nested = message.get(key)
        if isinstance(nested, str) and nested.strip():
            return nested.strip()

    return default


def _infer_skill(payload: Dict[str, Any], slang_line: str) -> str:
    """Infer skill name for status report payload."""
    details = payload.get("details")
    if isinstance(details, dict):
        for key in ("spell", "skill", "which_skill"):
            value = details.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    normalized = slang_line.lower()
    if "沒閃" in slang_line or "无闪" in slang_line or "no flash" in normalized:
        return "flash"
    if "沒大" in slang_line or "no r" in normalized:
        return "ultimate"
    if "沒傳" in slang_line or "沒tp" in normalized or "no tp" in normalized:
        return "teleport"
    if "沒治癒" in slang_line or "沒治" in slang_line:
        return "heal"
    if "沒淨化" in slang_line:
        return "cleanse"

    return "unknown"


def _send_udp_json(host: str, port: int, payload: Dict[str, Any]) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(json.dumps(payload, ensure_ascii=False).encode("utf-8"), (host, port))


def _send_countdown_start(
    host: str, port: int, timer_id: int, skill: str | None = None
) -> None:
    """Notify the Logi plugin countdown. Use skill 'teleport' for 傳送, 'flash' or None for 閃現 (legacy STARTn)."""
    if skill == "teleport":
        text = f"START{timer_id}T"
    elif skill == "flash":
        text = f"START{timer_id}F"
    else:
        text = f"START{timer_id}"
    signal = text.encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(signal, (host, port))


def _send_chat_to_game(lol_slang_text: str) -> None:
    # Keep the exact send flow used in test_voice_all_whisper.py (237-241).
    keyboard.send("enter")
    time.sleep(0.3)
    keyboard.write(lol_slang_text, delay=0.05)
    time.sleep(0.2)
    keyboard.send("enter")


def classify_and_route(
    payload: Dict[str, Any],
    rpi_ip: str,
    rpi_port: int,
    countdown_host: str,
    countdown_port: int,
) -> None:
    kind = _get_field(payload, "kind").lower()
    if not kind:
        raise ValueError("JSON missing 'kind'")

    target = _get_field(payload, "target")
    slang = _get_field(payload, "lol_slang_line")

    if kind == "status_report":
        skill = _infer_skill(payload, slang)
        status_payload = {
            "which character": target,
            "which skill": skill,
        }

        # 1) Send status to RPi for all players.
        _send_udp_json(rpi_ip, rpi_port, status_payload)
        print(f"Sent status_report to RPi {rpi_ip}:{rpi_port} -> {status_payload}")

        # 2) Send same JSON to countdown service.
        _send_udp_json(countdown_host, countdown_port, status_payload)
        print(f"Sent countdown payload to {countdown_host}:{countdown_port} -> {status_payload}")

        # 3) Trigger mapped skill cooldown for this target (flash vs teleport are separate).
        timer_id = HERO_TIMER_MAP.get(target)
        if timer_id is not None:
            cd_skill: str | None
            if skill == "teleport":
                cd_skill = "teleport"
            elif skill == "flash":
                cd_skill = "flash"
            else:
                cd_skill = None
            _send_countdown_start(
                countdown_host, countdown_port, timer_id, skill=cd_skill
            )
            suffix = "T" if cd_skill == "teleport" else ("F" if cd_skill == "flash" else "")
            print(
                f"Sent countdown START{timer_id}{suffix or ''} (skill={skill}) for target {target}"
            )
        else:
            print(f"No countdown mapping found for target: {target}")
        return

    if kind == "chat":
        if not slang:
            raise ValueError("chat payload missing 'lol_slang_line'")
        _send_chat_to_game(slang)
        print(f"Sent chat to game: {slang}")
        return

    raise ValueError(f"Unsupported kind: {kind}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify and route LOL message JSON.")
    parser.add_argument("json_file", help="Path to input JSON file.")
    parser.add_argument("--rpi-ip", default=DEFAULT_RPI_IP, help="RPi host.")
    parser.add_argument("--rpi-port", type=int, default=DEFAULT_RPI_PORT, help="RPi UDP port.")
    parser.add_argument("--countdown-host", default=DEFAULT_COUNTDOWN_HOST, help="Countdown host.")
    parser.add_argument("--countdown-port", type=int, default=DEFAULT_COUNTDOWN_PORT, help="Countdown UDP port.")
    args = parser.parse_args()

    with open(args.json_file, "r", encoding="utf-8") as f:
        payload = json.load(f)

    classify_and_route(
        payload=payload,
        rpi_ip=args.rpi_ip,
        rpi_port=args.rpi_port,
        countdown_host=args.countdown_host,
        countdown_port=args.countdown_port,
    )


if __name__ == "__main__":
    main()
