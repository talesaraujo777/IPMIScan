#!/usr/bin/env python3
import ipaddress
import json
import socket
import sys
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, render_template, request

PROJECT_ROOT = Path(__file__).resolve().parent
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))


PRESETS_FILE = PROJECT_ROOT / "data" / "presets.json"

app = Flask(
    __name__,
    template_folder=str(BUNDLE_ROOT / "templates"),
    static_folder=str(BUNDLE_ROOT / "static"),
)

MAX_HOSTS = 4096
DEFAULT_TIMEOUT = 0.8
DEFAULT_WORKERS = 200


def parse_network(mask, start_ip):
    if not mask:
        return None
    mask = mask.strip()
    if "/" in mask:
        return ipaddress.ip_network(mask, strict=False)
    return ipaddress.ip_network(f"{start_ip}/{mask}", strict=False)


def sanitize_preset(raw_preset, fallback_id):
    label = str(raw_preset.get("label", "")).strip()
    start_ip = str(raw_preset.get("start_ip", "")).strip()
    end_ip = str(raw_preset.get("end_ip", "")).strip()

    if not label or not start_ip or not end_ip:
        return None

    try:
        ipaddress.IPv4Address(start_ip)
        ipaddress.IPv4Address(end_ip)
    except ipaddress.AddressValueError:
        return None

    return {
        "id": str(raw_preset.get("id") or fallback_id),
        "label": label,
        "start_ip": start_ip,
        "end_ip": end_ip,
        "is_custom": bool(raw_preset.get("is_custom", True)),
    }


def load_custom_presets():
    if not PRESETS_FILE.exists():
        return []

    try:
        payload = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    presets = []
    for index, raw_preset in enumerate(payload if isinstance(payload, list) else []):
        preset = sanitize_preset(raw_preset, fallback_id=f"custom-{index}")
        if preset:
            preset["is_custom"] = True
            presets.append(preset)
    return presets


def save_custom_presets(presets):
    PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "id": preset["id"],
            "label": preset["label"],
            "start_ip": preset["start_ip"],
            "end_ip": preset["end_ip"],
        }
        for preset in presets
    ]
    PRESETS_FILE.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def get_all_presets():
    return load_custom_presets()


def build_preset_form_data():
    return {
        "label": "",
        "start_ip": "",
        "end_ip": "",
    }


def validate_preset(label, start_ip, end_ip):
    if not label or not start_ip or not end_ip:
        raise ValueError("Informe nome, IP inicial e IP final do preset")

    start = ipaddress.IPv4Address(start_ip)
    end = ipaddress.IPv4Address(end_ip)
    if int(end) < int(start):
        raise ValueError("No preset, o IP final deve ser maior ou igual ao IP inicial")

    return {
        "id": f"custom-{int(datetime.now().timestamp() * 1000)}",
        "label": label,
        "start_ip": str(start),
        "end_ip": str(end),
        "is_custom": True,
    }


def ip_range(start_ip, end_ip):
    start = ipaddress.IPv4Address(start_ip)
    end = ipaddress.IPv4Address(end_ip)
    if int(end) < int(start):
        raise ValueError("IP final deve ser maior ou igual ao IP inicial")
    current = int(start)
    last = int(end)
    while current <= last:
        yield ipaddress.IPv4Address(current)
        current += 1


def build_target(start_ip, end_ip, mask):
    if not start_ip or not end_ip or not mask:
        raise ValueError("Informe IP inicial, IP final e mascara")

    network = parse_network(mask, start_ip)

    start = ipaddress.IPv4Address(start_ip)
    end = ipaddress.IPv4Address(end_ip)

    if network and (start not in network or end not in network):
        raise ValueError("Intervalo fora da mascara informada")

    count = int(end) - int(start) + 1
    return f"{start}-{end}", count


def build_probe_packet():
    return bytes([
        0x06, 0x00, 0xFF, 0x06,
        0x00, 0x00, 0x11, 0xBE,
        0x80, 0x00, 0x00, 0x00,
    ])


def probe_ip(ip, timeout, packet):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.sendto(packet, (str(ip), 623))
            data, _ = sock.recvfrom(1024)
            if len(data) >= 12 and data[0] == 0x06 and data[2] == 0xFF:
                return True
            return True
        except socket.timeout:
            return False
        except OSError:
            return False


def scan_ipmi(start_ip, end_ip, mask, timeout, workers):
    network = parse_network(mask, start_ip)
    start = ipaddress.IPv4Address(start_ip)
    end = ipaddress.IPv4Address(end_ip)

    if network and (start not in network or end not in network):
        raise ValueError("Intervalo fora da mascara informada")

    targets = []
    for ip in ip_range(str(start), str(end)):
        if network and ip not in network:
            continue
        targets.append(ip)

    if not targets:
        return []

    packet = build_probe_packet()
    results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(probe_ip, ip, timeout, packet): ip
            for ip in targets
        }
        for future in as_completed(future_map):
            ip = future_map[future]
            try:
                if future.result():
                    results.append({
                        "ip": str(ip),
                        "state": "rmcp",
                        "service": "ipmi",
                    })
            except Exception:
                pass

    return results


@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    error = None
    meta = {}
    preset_message = None
    presets = get_all_presets()
    form_data = {
        "start_ip": "",
        "end_ip": "",
        "mask": "",
    }
    preset_form_data = build_preset_form_data()
    if request.method == "POST":
        action = (request.form.get("action") or "scan").strip()

        if action == "save_preset":
            preset_form_data = {
                "label": (request.form.get("preset_label") or "").strip(),
                "start_ip": (request.form.get("preset_start_ip") or "").strip(),
                "end_ip": (request.form.get("preset_end_ip") or "").strip(),
            }
            try:
                new_preset = validate_preset(
                    preset_form_data["label"],
                    preset_form_data["start_ip"],
                    preset_form_data["end_ip"],
                )
                custom_presets = load_custom_presets()
                custom_presets.append(new_preset)
                save_custom_presets(custom_presets)
                presets = get_all_presets()
                preset_form_data = build_preset_form_data()
                preset_message = "Preset salvo com sucesso."
            except Exception as exc:
                error = str(exc)

        elif action == "delete_preset":
            preset_id = (request.form.get("preset_id") or "").strip()
            try:
                custom_presets = load_custom_presets()
                updated_presets = [preset for preset in custom_presets if preset["id"] != preset_id]
                if len(updated_presets) == len(custom_presets):
                    raise ValueError("Preset nao encontrado.")
                save_custom_presets(updated_presets)
                presets = get_all_presets()
                preset_message = "Preset removido com sucesso."
            except Exception as exc:
                error = str(exc)

        else:
            form_data = {
                "start_ip": (request.form.get("start_ip") or "").strip(),
                "end_ip": (request.form.get("end_ip") or "").strip(),
                "mask": (request.form.get("mask") or "").strip(),
            }
            start_ip = form_data["start_ip"]
            end_ip = form_data["end_ip"]
            mask = form_data["mask"]

            try:
                target, count = build_target(start_ip, end_ip, mask)
                if count > MAX_HOSTS:
                    raise ValueError(f"Intervalo muito grande ({count} hosts). Limite: {MAX_HOSTS}.")

                results = scan_ipmi(
                    start_ip,
                    end_ip,
                    mask,
                    timeout=DEFAULT_TIMEOUT,
                    workers=DEFAULT_WORKERS,
                )
                meta = {
                    "target": target,
                    "count": count,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "found": len(results),
                }
            except Exception as exc:
                error = str(exc)

    return render_template(
        "index.html",
        results=results,
        error=error,
        meta=meta,
        form_data=form_data,
        preset_form_data=preset_form_data,
        preset_message=preset_message,
        presets=presets,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
