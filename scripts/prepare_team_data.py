"""从上级项目 Roco-dashboard 的真实快照生成模块 B 演示数据（脱敏）。

输入全部只读，产物只写入本仓库 模块B：阵容识别与性格推荐/data.js。
可重跑：python scripts/prepare_team_data.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent / "Roco-dashboard"
MOD = ROOT / "模块B：阵容识别与性格推荐"
OUT = MOD / "data.js"

SAMPLE_3COL = PARENT / "scripts/testdata/ocr_real_sample_3col.json"
SAMPLE_WOLF = PARENT / "scripts/testdata/ocr_real_sample_wolf.json"
NATURES_JS = PARENT / "cloudfunctions/teamOcr/natures.js"
POOL_NAMES = PARENT / "cloudfunctions/teamOcr/pool_names.json"
POOL_SKILLS = PARENT / "cloudfunctions/teamOcr/pool_skills.json"
GRAD_REC = PARENT / "dashboard/grad_rec.json.bare_bak"
PETS = PARENT / "dashboard/_pets.json"

# 图鉴名与推荐表最终形态名的同编号别名（图鉴编号 286）
REC_ALIAS = {"圣剑-X": "X_圣剑"}

# 取自上级项目 scripts/selftest_teamocr.js 第 8/9 节的断言，demo 只做展示不重跑 OCR
SAMPLES = [
    {
        "id": "team-3col",
        "title": "48期 · 无敌平衡队",
        "layout": "2 行 3 列",
        "source": "scripts/testdata/ocr_real_sample_3col.json",
        "mode": "direct",
        "det_file": SAMPLE_3COL,
        "notes": [
            "旧 findAnchors 每行只取前 2 个命中，魔力猫 / 罗隐必被丢；按 cy 聚行后取整行命中修复。",
            "技能归属用非对称窗口 [cx-80, cx+colGap×0.8]，半径固定 300px，避免跨行串列。",
            "这份模板性格直接 OCR 出「平和 / 聪明 / …」，不需要增益减益反查。",
        ],
        "cells": [
            {"name": "圣剑-X", "raw": "圣剑-X", "match": "exact", "nature": "平和", "natureSource": "direct",
             "evidence": ["平和"], "quals": [], "skills": ["齿轮扭矩", "啮合传递", "休息回复", "拖拉机"]},
            {"name": "火羽", "raw": "火羽", "match": "exact", "nature": "聪明", "natureSource": "direct",
             "evidence": ["聪明"], "quals": [], "skills": ["焚烧烙印", "高温回火", "回旋风暴", "幽灵爆发"]},
            {"name": "魔力猫", "raw": "魔力猫", "match": "exact", "nature": "踏实", "natureSource": "direct",
             "evidence": ["踏实"], "quals": [], "skills": ["藤绞", "移花接木", "仙人掌刺击", "光合作用"]},
            {"name": "锤头鹳", "raw": "锤头鹳", "match": "exact", "nature": "沉默", "natureSource": "direct",
             "evidence": ["沉默"], "quals": [], "skills": ["水弹枪", "晒太阳", "恶意逃离", "洗礼"]},
            {"name": "罗隐", "raw": "罗隐", "match": "exact", "nature": "固执", "natureSource": "direct",
             "evidence": ["固执"], "quals": [], "skills": ["先发制人", "地刺", "彼岸之手", "泥浆铠甲"]},
            {"name": "霹雳迪迪", "raw": "霹雳迪迪", "match": "exact", "nature": "胆小", "natureSource": "direct",
             "evidence": ["胆小"], "quals": [], "skills": ["色散", "落雷", "镜像反射", "放晴"]},
        ],
    },
    {
        "id": "team-wolf",
        "title": "狼王队 · 水印粘连",
        "layout": "3 行 2 列",
        "source": "scripts/testdata/ocr_real_sample_wolf.json",
        "mode": "derived",
        "det_file": SAMPLE_WOLF,
        "notes": [
            "weak 补位先过滤属性串 / 标签词，再按「含图鉴名子串优先」补空位，真名不会被伪行挤出。",
            "「卡瓦重噜球狼王」= 卡瓦重 + 作者水印，exact/fuzzy 都失败后由 matchNamePrefix 认出卡瓦重。",
            "这份模板只 OCR 出增益 / 减益两个文本框，性格由 (增益, 减益) 在 30 条性格表里唯一反查。",
        ],
        "cells": [
            {"name": "巨噬针鼹", "raw": "巨噬针鼹", "match": "exact", "gain": "物攻", "loss": "魔攻",
             "natureSource": "derived", "evidence": ["物攻", "魔攻"], "quals": ["物攻", "生命", "魔防"],
             "skills": ["先发制人", "冰爪", "地刺", "压扁"]},
            {"name": "卡瓦重", "raw": "卡瓦重噜球狼王", "match": "prefix", "gain": "速度", "loss": "魔攻",
             "natureSource": "derived", "evidence": ["速度", "魔攻"], "quals": ["物攻", "生命", "速度"],
             "skills": ["取念", "拟寄生", "筛管窝流", "火焰切割"]},
            {"name": "翠顶夫人", "raw": "翠顶夫人", "match": "exact", "gain": "物攻", "loss": "魔攻",
             "natureSource": "derived", "evidence": ["物攻", "魔攻"], "quals": ["物攻", "生命", "速度"],
             "skills": ["力量增效", "水刃", "俯冲猛击", "水环"]},
            {"name": "化蝶", "raw": "化蝶", "match": "exact", "gain": "魔攻", "loss": "物攻",
             "natureSource": "derived", "evidence": ["魔攻", "物攻"], "quals": ["物防", "生命", "魔攻"],
             "skills": ["虫蛊", "超维投射", "破罐破摔", "掩护"]},
            {"name": "布灵布灵", "raw": "布灵布灵", "match": "exact", "gain": "速度", "loss": "魔攻",
             "natureSource": "derived", "evidence": ["速度", "魔攻"], "quals": ["物攻", "生命", "速度"],
             "skills": ["取念", "叠加态", "透镜实验", "影袭"]},
            {"name": "恶魔狼", "raw": "恶魔狼", "match": "exact", "gain": "物攻", "loss": "魔攻",
             "natureSource": "derived", "evidence": ["物攻", "魔攻"], "quals": ["物攻", "生命", "魔防"],
             "skills": ["蝙蝠", "先发制人", "惊吓盒子", "火焰切割"]},
        ],
    },
]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_catalog(names, pets):
    by_name = {}
    for pet in pets:
        by_name.setdefault(pet["name"], []).append(pet)
    catalog = {}
    for name in names:
        rows = by_name.get(name) or by_name.get(REC_ALIAS.get(name, ""), [])
        if not rows:
            raise SystemExit(f"[模块B] 图鉴缺条目：{name}")
        pet = min(rows, key=lambda p: p["pet_id"])
        ratio = pet.get("gender_ratio") or {}
        eggs = [("大地组" if g == "岩石组" else g) for g in (pet.get("egg_group_names") or [])]
        catalog[name] = {
            "pid": pet["pet_id"],
            "dex": pet.get("handbook_no", ""),
            "eggs": eggs,
            "gender": f"♂{ratio.get('male_percent', '?')}% / ♀{ratio.get('female_percent', '?')}%",
            "season": pet.get("season_id", 0),
            "shiny": bool(pet.get("has_shiny")),
            "alias": REC_ALIAS.get(name, ""),
            "icon": f"gtimg jingling/{pet['pet_id']}/icon.png",
            "art": f"shallow pets/{pet['pet_id']}/icon.png",
        }
    return catalog


def build_recs(grad_rows, names):
    index = {name: {} for name in names}
    for row in grad_rows:
        if len(row) < 7:
            continue
        final, nature, level, qual = row[3], row[4], row[5], row[6]
        if not final or not nature:
            continue
        for name in names:
            if final == REC_ALIAS.get(name, name):
                key = (nature, level)
                item = {"nature": nature, "level": level, "qual": qual, "dex": row[0]}
                if key not in index[name] or (not index[name][key]["qual"] and qual):
                    index[name][key] = item
    return {name: list(items.values()) for name, items in index.items()}


def main():
    natures_src = NATURES_JS.read_text(encoding="utf-8")
    natures = [
        {"nature": n, "gain": g, "loss": l}
        for n, g, l in re.findall(r'\{\s*nature:\s*"([^"]+)",\s*gain:\s*"([^"]+)",\s*loss:\s*"([^"]+)"\s*\}', natures_src)
    ]
    if len(natures) != 30:
        raise SystemExit(f"[模块B] 性格表应为 30 条，实得 {len(natures)}")

    nature_map = {(n["gain"], n["loss"]): n["nature"] for n in natures}
    pool_names = set(load_json(POOL_NAMES))
    pool_skills = set(load_json(POOL_SKILLS))
    pets = load_json(PETS)["pets"]
    grad_rows = load_json(GRAD_REC)["grad_recs"]

    samples = []
    all_names = {c["name"] for s in SAMPLES for c in s["cells"]}
    recs = build_recs(grad_rows, all_names)
    catalog = build_catalog(all_names, pets)

    for spec in SAMPLES:
        dets = load_json(spec["det_file"])
        cells = []
        for i, src in enumerate(spec["cells"], 1):
            name = src["name"]
            nature = src.get("nature") or nature_map.get((src["gain"], src["loss"]), "")
            if not nature:
                raise SystemExit(f"[模块B] 性格反查失败：{src['raw']} / {src.get('gain')}→{src.get('loss')}")
            skills = [{"name": s, "inPool": s in pool_skills} for s in src["skills"]]
            cells.append({
                "idx": i,
                "row": (i - 1) // (3 if spec["layout"] == "2 行 3 列" else 2) + 1,
                "col": (i - 1) % (3 if spec["layout"] == "2 行 3 列" else 2) + 1,
                "name": name,
                "raw": src["raw"],
                "match": src["match"],
                "inNamePool": name in pool_names,
                "nature": nature,
                "natureSource": src["natureSource"],
                "gain": src.get("gain", ""),
                "loss": src.get("loss", ""),
                "evidence": src["evidence"],
                "quals": src["quals"],
                "skills": skills,
                "recs": recs.get(name, []),
                "codex": catalog[name],
            })
        samples.append({
            "id": spec["id"],
            "title": spec["title"],
            "layout": spec["layout"],
            "source": spec["source"],
            "mode": spec["mode"],
            "notes": spec["notes"],
            "board": {
                "w": max(d["x2"] for d in dets) + 40,
                "h": max(d["y2"] for d in dets) + 40,
            },
            "dets": dets,
            "cells": cells,
        })

    payload = {
        "meta": {
            "title": "阵容识别 → 性格推荐 → 图鉴链路",
            "sourceProject": "Roco-dashboard",
            "note": "OCR 检测框来自真实缓存样本；识别结论按上级项目 selftest 断言整理；不含原图、UID、账号或精确时间戳。",
            "poolNames": len(pool_names),
            "poolSkills": len(pool_skills),
            "natureRules": len(natures),
            "gradRows": len(grad_rows),
        },
        "natures": natures,
        "samples": samples,
    }
    MOD.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "window.TEAM_DEMO_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print(f"[模块B] 已生成 {OUT.relative_to(ROOT)}")
    for sample in samples:
        print(f"  {sample['title']}: dets={len(sample['dets'])} cells={len(sample['cells'])}")


if __name__ == "__main__":
    main()
