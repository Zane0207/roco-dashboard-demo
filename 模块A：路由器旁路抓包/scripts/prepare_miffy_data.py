"""从上级项目 Miffy 快照生成模块 A 演示数据（脱敏）。

脱敏规则：
- 保留玩家昵称 "Miffy" 用于叙事
- 去掉 UID、源文件名、精确时间戳（generatedAt/sourceTs/importedAt/obtainedAt）
- 保留数据形态、统计特征与业务字段
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT.parent / "Roco-dashboard" / "dashboard" / "assets" / "boxes_Miffy.json"
OUT = ROOT / "modules" / "A-capture" / "data.js"

DROP_META = {"sourceFile", "sourceTs", "sourceTsEpoch", "importedAt", "generatedAt"}
DROP_PET = {"obtainedAt", "obtainedAtUnix", "acquisitionWorldId", "acquisitionSourceId"}
KEEP_PET = [
    "gid", "name", "spriteName", "gender", "nature", "speciesPetId",
    "heightCm", "weightKg", "weightPercent", "bodyMedal", "voiceDb", "voiceMedal",
    "isShiny", "isColorful", "colorfulColor", "colorfulColorNo",
    "level", "individualStats", "individualBonuses", "individualTotal",
    "bloodline", "acquisitionBallName", "acquisitionType", "acquisitionLocationName",
    "speciesBaseName", "protocolBaseStats",
]


def main():
    src = json.loads(SRC.read_text(encoding="utf-8"))

    meta = {k: v for k, v in src["meta"].items() if k not in DROP_META}
    meta["player"] = "Miffy"
    meta["snapshotLabel"] = "玩家背包快照 · 已脱敏"

    boxes = []
    for box in src["boxes"]:
        pets = []
        for pet in box.get("pets", []):
            row = {k: pet.get(k) for k in KEEP_PET if k in pet}
            pets.append(row)
        boxes.append({
            "boxNumber": box.get("boxNumber"),
            "boxName": box.get("boxName"),
            "lock": box.get("lock", False),
            "count": box.get("count", len(pets)),
            "pets": pets,
        })

    all_pets = [p for b in boxes for p in b["pets"]]
    stats = {
        "boxCount": len(boxes),
        "petCount": len(all_pets),
        "shinyCount": sum(1 for p in all_pets if p.get("isShiny")),
        "colorfulCount": sum(1 for p in all_pets if p.get("isColorful")),
        "fullBoxes": sum(1 for b in boxes if b["count"] >= 30),
    }

    payload = {"meta": meta, "stats": stats, "boxes": boxes}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "window.DEMO_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")
    print("stats:", json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
