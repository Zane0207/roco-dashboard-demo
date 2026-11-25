#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把上级项目从真实 pcap 解出的事件 JSONL + boxes 快照转成 demo 用的 replay_data.js。

原始 pcap 与会话密钥不进仓库；本脚本只做脱敏与裁剪：
- 时间戳改为相对毫秒
- 去掉 UID / 账号 / 玩家名 / 精确时间 / 原始帧
- m5 去掉 enemy_side（UID）与 game_id（实例号），宠物名用快照本地表还原

用法：
    python3 build_replay_from_pcap.py \
        --events  <run.py 输出的契约事件 JSONL> \
        --snapshot <pcap_replay.py 输出的 *_boxes.json> \
        --out ../模块A：路由器旁路抓包/replay_data.js
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def scrub_snapshot(path: Path) -> tuple[dict, dict[int, str], list[dict]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    boxes = doc.get("boxes") or []
    pets = [p for b in boxes for p in (b.get("pets") or [])]
    names: dict[int, str] = {}
    for p in pets:
        pid = p.get("speciesPetId")
        if pid and p.get("name"):
            names.setdefault(int(pid), str(p["name"]))

    stats = {
        "boxCount": len(boxes),
        "petCount": len(pets),
        "shinyCount": sum(1 for p in pets if p.get("isShiny")),
        "colorfulCount": sum(1 for p in pets if p.get("isColorful")),
    }

    slim_boxes = []
    for b in boxes[:6]:
        slim_pets = []
        for p in (b.get("pets") or [])[:3]:
            slim_pets.append({
                "name": p.get("name") or "—",
                "speciesPetId": p.get("speciesPetId"),
                "gender": p.get("gender") or "",
                "nature": p.get("nature") or "",
                "level": p.get("level"),
                "weightPercent": p.get("weightPercent"),
                "isShiny": bool(p.get("isShiny")),
                "isColorful": bool(p.get("isColorful")),
            })
        slim_boxes.append({
            "boxNumber": b.get("boxNumber"),
            "count": b.get("count") or len(b.get("pets") or []),
            "pets": slim_pets,
        })

    eggs = ((doc.get("collections") or {}).get("eggInventory") or {}).get("eggs") or []
    stats["eggCount"] = len(eggs)
    egg_samples = []
    for e in eggs[:5]:
        egg_samples.append({
            "egg_id": str(e.get("externalEggId") or ""),
            "item_id": e.get("itemConfId"),
            "pet_id": e.get("petConfId") or e.get("speciesPetId"),
            "pet_name": e.get("petName") or e.get("petDisplayName") or "—",
            "weight_g": e.get("weightGrams"),
            "hatch_seconds": e.get("hatchSeconds"),
            "is_shiny": bool(e.get("isShiny")),
            "is_colorful": bool(e.get("isColorful")),
            "recognized": bool(e.get("recognized")),
        })
    return {"stats": stats, "boxes": slim_boxes}, names, egg_samples


def pick_events(events: list[dict]) -> list[dict]:
    picked: list[int] = []

    def add_first(pred) -> None:
        for i, e in enumerate(events):
            if i not in picked and pred(e):
                picked.append(i)
                return

    add_first(lambda e: e.get("state") == "key_captured")
    add_first(lambda e: e.get("state") == "flow_created")
    add_first(lambda e: e.get("opcode") == 258)
    add_first(lambda e: e.get("opcode") == 338)
    for _ in range(3):
        add_first(lambda e: e.get("opcode") == 4934)
    add_first(lambda e: e.get("state") == "decrypt_fail")
    add_first(lambda e: e.get("opcode") == 4886 and isinstance(e.get("m5"), dict))
    add_first(lambda e: e.get("opcode") == 4890)
    add_first(lambda e: e.get("opcode") == 4900)
    add_first(lambda e: e.get("opcode") == 579)
    add_first(lambda e: e.get("opcode") == 4908)
    add_first(lambda e: e.get("state") == "flow_closed")
    return [events[i] for i in sorted(picked)]


def scrub_m5(m5: dict, names: dict[int, str]) -> dict:
    units = []
    for u in m5.get("units") or []:
        pid = u.get("pet_id")
        units.append({
            "slot": u.get("slot"),
            "pet_id": pid,
            "name": names.get(int(pid), "未知精灵") if pid else "未知精灵",
            "level": u.get("level"),
            "gender": u.get("gender"),
            "mutation": u.get("mutation") or 0,
            "blood_id": u.get("blood_id"),
            "nature_id": u.get("nature_id"),
            "voice": u.get("voice"),
            "bonus": u.get("bonus"),
            "height_cm": u.get("height_cm"),
            "weight_g": u.get("weight_g"),
        })
    return {
        "battle_id": str(m5.get("battle_id") or ""),
        "mode": m5.get("mode"),
        "enter_type": m5.get("enter_type"),
        "target_slot": m5.get("target_slot"),
        "units": units,
    }


def scrub_events(events: list[dict], names: dict[int, str]) -> list[dict]:
    t0 = events[0].get("ts", 0) if events else 0
    flow_map: dict[str, str] = {}
    out = []
    for e in events:
        fid = str(e.get("flow_id") or "")
        if fid not in flow_map:
            flow_map[fid] = "设备 " + chr(65 + len(flow_map))
        row = {
            "ts": int(round((float(e.get("ts", t0)) - t0) * 1000)),
            "flow_id": fid,
            "src": flow_map[fid],
            "dir": e.get("dir"),
            "opcode": e.get("opcode"),
            "raw_len": e.get("raw_len"),
            "confidence": e.get("confidence"),
            "event_kind": e.get("event_kind"),
        }
        for key in ("state", "msg_name", "fields", "field_confidence", "unknown", "unknown_count"):
            if key in e:
                row[key] = e[key]
        if isinstance(e.get("diag"), dict):
            row["diag"] = {k: e["diag"][k] for k in ("frame_seq", "wire_len", "body_len", "hdr_len", "magic_offset") if k in e["diag"]}
        if isinstance(e.get("m5"), dict):
            row["m5"] = scrub_m5(e["m5"], names)
        out.append(row)
    return out


SEGMENTS = [
    ("抓包链路", 0, 30),
    ("收蛋", 100, 115),
    ("战斗进场", 790, 820),
    ("战斗结束", 1060, 1072),
]


def build_stream(events: list[dict], names: dict[int, str]) -> tuple[list[dict], list[dict]]:
    """拼接真实 pcap 的 4 个窗口：段内保留真实间隔，段间留 1s。"""
    t0 = events[0].get("ts", 0)
    out: list[dict] = []
    meta: list[dict] = []
    cursor_ms = 0
    for label, lo, hi in SEGMENTS:
        seg = [e for e in events if lo <= float(e.get("ts", t0)) - t0 <= hi]
        if not seg:
            continue
        rows = scrub_events(seg, names)
        for row in rows:
            row["ts"] = cursor_ms + row["ts"]
            row["seg"] = label
        out.extend(rows)
        meta.append({"label": label, "from_s": lo, "to_s": hi, "events": len(rows)})
        cursor_ms += int(round((float(seg[-1].get("ts", t0)) - float(seg[0].get("ts", t0))) * 1000)) + 1000
    return out, meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", required=True, type=Path)
    ap.add_argument("--snapshot", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    events = load_jsonl(args.events)
    if not events:
        raise SystemExit("events JSONL 为空")
    snapshot, names, eggs = scrub_snapshot(args.snapshot)
    chosen = pick_events(events)
    if not any(isinstance(e.get("m5"), dict) for e in chosen):
        raise SystemExit("所选事件里没有 4886 M5，无法生成战斗卡")

    battle = next(scrub_m5(e["m5"], names) for e in chosen if isinstance(e.get("m5"), dict))
    egg = eggs[0] if eggs else {}
    stream, segments = build_stream(events, names)

    payload = {
        "source": "real-pcap-derived",
        "note": "事件来自本地真实 pcap 离线解析；连续流为 4 个真实窗口按原时间拼接，段内保留真实间隔，段间 1s",
        "stats": snapshot["stats"],
        "boxes": snapshot["boxes"],
        "battle": battle,
        "egg": egg,
        "events": scrub_events(chosen, names),
        "stream": stream,
        "stream_count": len(stream),
        "segments": segments,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "window.REPLAY_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print(f"wrote {args.out} · events={len(chosen)} stats={payload['stats']}")


if __name__ == "__main__":
    main()
