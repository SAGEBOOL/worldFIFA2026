#!/usr/bin/env python3
"""世界杯每日数据测试报告生成器 v3.0

从 worldcup26.ir API 获取数据，生成 Markdown 测试报告。
API 字段: home_team_name_en, away_team_name_en, home_score, away_score,
         finished, local_date (MM/DD/YYYY HH:MM), type, group,
         home_scorers (JSON string), away_scorers, shootouts 等
"""

import json
import re
import urllib.request
from datetime import datetime
from collections import defaultdict

API_URL = "https://worldcup26.ir/get/games"
REPORT_DIR = "/Volumes/D/WorkBuddy/worldFIFA2026"
WEB_URL = "https://sagebool.github.io/worldFIFA2026/"


def fetch_games():
    """获取 API 比赛数据"""
    print(f"[INFO] 获取 API 数据: {API_URL}")
    req = urllib.request.Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    games = data.get("games", []) if isinstance(data, dict) else data
    print(f"✅ 获取到 {len(games)} 场比赛")
    return games


def check_sites():
    """检查网站可达性"""
    results = {}
    for name, url in [("世界杯宣传站", WEB_URL), ("数据源 site", "https://worldcup26.ir")]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            t0 = datetime.now()
            with urllib.request.urlopen(req, timeout=15) as r:
                elapsed = (datetime.now() - t0).total_seconds()
                results[name] = {"ok": True, "code": r.status, "latency_ms": round(elapsed * 1000)}
        except Exception as e:
            results[name] = {"ok": False, "error": str(e)[:100]}
    return results


def parse_date(date_str):
    """解析 local_date 为 date 对象 (格式: MM/DD/YYYY HH:MM)"""
    try:
        return datetime.strptime(date_str.strip(), "%m/%d/%Y %H:%M").date()
    except:
        try:
            return datetime.strptime(date_str.strip(), "%m/%d/%Y").date()
        except:
            return None


def parse_scorers(scorers_json):
    """解析射手 JSON 字符串 -> [(player_name, minute), ...]"""
    if not scorers_json or scorers_json == "null":
        return []
    try:
        lst = json.loads(scorers_json)
        players = []
        for item in lst:
            # 格式: "Player Name 27'" or "Player Name (90+4')"
            m = re.match(r'^(.+?)\s+\((.+?)\)', item)
            if m:
                players.append({"name": m.group(1).strip(), "minute": m.group(2)})
            else:
                # 尝试 "Name 27'"
                mm = re.match(r'^(.+?)\s+(\d+\'?)$', item.strip('" '))
                if mm:
                    players.append({"name": mm.group(1).strip(), "minute": mm.group(2)})
                else:
                    players.append({"name": item.strip('" '), "minute": "?"})
        return players
    except:
        return []


def get_today_games(games, today):
    return [g for g in games if parse_date(g.get("local_date", "")) == today]


def get_finished(games):
    return [g for g in games if g.get("finished") == "TRUE"]


def calc_scorers_rank(games, top_n=5):
    """全局射手榜 Top N"""
    goals = defaultdict(lambda: {"name": "", "goals": 0, "team": ""})
    for g in games:
        if g.get("finished") != "TRUE":
            continue
        home = g.get("home_team_name_en", "")
        away = g.get("away_team_name_en", "")
        for raw in [g.get("home_scorers"), g.get("away_scorers")]:
            if not raw or raw == "null":
                continue
            try:
                lst = json.loads(raw)
            except:
                continue
            scored_by = home if lst else away  # 简化判断
            for item in lst:
                m = re.match(r'^(.+?)\s+', item.strip('" '))
                if m:
                    pname = m.group(1).strip()
                    if pname:
                        goals[pname]["goals"] += 1
                        goals[pname]["team"] = home
                goals[pname]["name"] = item.strip('" ')
    ranked = sorted(goals.values(), key=lambda x: -x["goals"])[:top_n]
    return ranked


def calc_stats(games):
    """赛事统计数据"""
    finished = get_finished(games)
    total_goals = 0
    home_wins = away_wins = draws = 0
    highest = {"teams": "", "total": 0}

    for g in finished:
        hs = int(g.get("home_score", 0))
        ascore = int(g.get("away_score", 0))
        total = hs + ascore
        total_goals += total
        if total > highest["total"]:
            highest = {"teams": f"{g.get('home_team_name_en','')} vs {g.get('away_team_name_en','')}", "score": f"{hs}-{ascore}", "total": total}
        if hs > ascore:
            home_wins += 1
        elif ascore > hs:
            away_wins += 1
        else:
            draws += 1

    # 点球大战场次
    pen_shootouts = 0
    for g in games:
        if g.get("type") == "group":
            continue
        hs = int(g.get("home_score", 0))
        ascore = int(g.get("away_score", 0))
        if hs == ascore and g.get("finished") == "TRUE":
            # Check shootout data
            if g.get("home_penalty_score") or g.get("away_penalty_score"):
                pen_shootouts += 1

    return {
        "total": len(finished),
        "goals": total_goals,
        "avg": round(total_goals / len(finished), 2) if finished else 0,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "pen_shootouts": pen_shootouts,
        "highest": highest
    }


def calc_group_standings(games):
    """小组积分榜"""
    groups = defaultdict(lambda: defaultdict(lambda: {"p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}))
    group_letters = "ABCDEFGHIJKL"

    for g in games:
        if g.get("finished") != "TRUE":
            continue
        grp = g.get("group", "").upper()
        if grp not in group_letters:
            continue
        home = g.get("home_team_name_en", "")
        away = g.get("away_team_name_en", "")
        hs = int(g.get("home_score", 0))
        ascore = int(g.get("away_score", 0))

        t = groups[grp]
        if home not in t:
            t[home] = {"p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}
        if away not in t:
            t[away] = {"p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}

        t[home]["p"] += 1
        t[away]["p"] += 1
        t[home]["gf"] += hs
        t[home]["ga"] += ascore
        t[away]["gf"] += ascore
        t[away]["ga"] += hs

        if hs > ascore:
            t[home]["w"] += 1; t[home]["pts"] += 3; t[away]["l"] += 1
        elif ascore > hs:
            t[away]["w"] += 1; t[away]["pts"] += 3; t[home]["l"] += 1
        else:
            t[home]["d"] += 1; t[away]["d"] += 1; t[home]["pts"] += 1; t[away]["pts"] += 1

    return {grp: sorted(t.items(), key=lambda x: (-x[1]["pts"], -(x[1]["gf"]-x[1]["ga"]), x[1]["gf"])) for grp, t in groups.items()}


def gen_report(games):
    now = datetime.now()
    today = now.date()
    today_str = now.strftime("%Y-%m-%d")

    # 子数据
    sites = check_sites()
    today_games = get_today_games(games, today)
    finished_all = get_finished(games)
    scorers = calc_scorers_rank(games)
    stats = calc_stats(games)
    standings = calc_group_standings(games)

    # 淘汰赛
    knockout = [g for g in finished_all if g.get("group") not in "ABCDEFGHIJKL"]
    r32_all = [g for g in games if g.get("type") == "r32"]
    r32_done = [g for g in r32_all if g.get("finished") == "TRUE"]

    lines = []
    lines.append(f"# 世界杯每日数据测试报告\n")
    lines.append(f"**报告日期**: {today_str}")
    lines.append(f"**数据来源**: [worldcup26.ir](https://worldcup26.ir)")
    lines.append(f"**宣传站**: [{WEB_URL}]({WEB_URL})\n")
    lines.append("---\n")

    # 1. 健康检查
    lines.append("## 1. 健康检查\n")
    lines.append("| 站点 | 状态 | 响应时间 |")
    lines.append("|------|------|----------|")
    for name, info in sites.items():
        icon = "✅ 正常" if info["ok"] else "❌ 异常"
        lat = f"{info['latency_ms']} ms" if info["ok"] else info.get("error", "未知")
        lines.append(f"| {name} | {icon} | {lat} |")
    all_ok = all(v["ok"] for v in sites.values())
    lines.append(f"\n**整体状态**: {'✅ 全部正常' if all_ok else '⚠️ 部分异常'}\n")

    # 2. 今日赛程
    lines.append("## 2. 今日赛程\n")
    lines.append(f"**日期**: {now.strftime('%Y年%m月%d日')} — **共 {len(today_games)} 场**\n")
    if not today_games:
        lines.append("> 今天暂无安排比赛。\n")
    else:
        for g in today_games:
            h = g.get("home_team_name_en", "")
            a = g.get("away_team_name_en", "")
            td = g.get("local_date", "")[:10]
            grp = g.get("group", "")
            st = g.get("finished")
            if st == "TRUE":
                hs = g.get("home_score", "?")
                ascore = g.get("away_score", "?")
                lines.append(f"- ✅ **{h} {hs} - {ascore} {a}** ({grp}组)")
            else:
                lines.append(f"- ⏳ {td} {h} vs {a} ({grp}组)")
    lines.append("")

    # 3. 赛事统计
    lines.append("## 3. 赛事统计\n")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总场次 (已完成) | {stats['total']} |")
    lines.append(f"| 总进球数 | {stats['goals']} |")
    lines.append(f"| 场均进球 | {stats['avg']} |")
    lines.append(f"| 主队胜 | {stats['home_wins']} |")
    lines.append(f"| 客队胜 | {stats['away_wins']} |")
    lines.append(f"| 平局 | {stats['draws']} |")
    lines.append(f"| 点球大战 | {stats['pen_shootouts']} |")
    if stats["highest"]["total"] > 0:
        h = stats["highest"]
        lines.append(f"\n### 最高比分\n- {h['teams']}: **{h['score']}** ({h['total']}球)\n")
    lines.append("---\n")

    # 4. 射手榜 Top 5
    lines.append("## 4. 射手榜 Top 5\n")
    lines.append("| 排名 | 球员 | 进球 | 球队 |")
    lines.append("|------|------|------|------|")
    for i, s in enumerate(scorers, 1):
        lines.append(f"| {i} | {s['name']} | {s['goals']} | {s['team']} |")
    lines.append("\n---\n")

    # 5. 小组积分榜
    lines.append("## 5. 小组积分榜\n")
    for grp in "ABCDEFGHIJKL":
        if grp in standings and standings[grp]:
            lines.append(f"### {grp} 组\n")
            lines.append("| 排名 | 球队 | 场次 | 胜 | 平 | 负 | 进球 | 失球 | 净胜球 | 积分 |")
            lines.append("|------|------|------|----|----|----|------|------|---------|------|")
            for j, (team, d) in enumerate(standings[grp], 1):
                gd = d["gf"] - d["ga"]
                lines.append(f"| {j} | {team} | {d['p']} | {d['w']} | {d['d']} | {d['l']} | {d['gf']} | {d['ga']} | {gd:+d} | {d['pts']} |")
            lines.append("")
    lines.append("---\n")

    # 6. 淘汰赛进度
    lines.append("## 6. 淘汰赛进度\n")
    lines.append(f"- **32 强赛**: {len(r32_done)}/{len(r32_all)} 场完成")
    if 0 < len(r32_done) < len(r32_all):
        lines.append(" (进行中)")
    elif len(r32_done) == len(r32_all) and r32_all:
        lines.append(" (全部完成)")
    lines.append("\n")

    if knockout:
        lines.append("### 已完成淘汰赛\n")
        for g in sorted(knockout, key=lambda x: x.get("local_date", "")):
            h = g.get("home_team_name_en", "")
            a = g.get("away_team_name_en", "")
            hs = g.get("home_score", 0)
            ascore = g.get("away_score", 0)
            stage = g.get("type", "")
            stage_map = {"r32": "32强", "r16": "16强", "qf": "8强", "sf": "半决赛", "third": "季军赛", "final": "决赛"}
            sn = stage_map.get(stage, stage)
            pen = ""
            if int(hs) == int(ascore) and (g.get("home_penalty_score") or g.get("away_penalty_score")):
                winner = "主队" if int(g.get("home_penalty_score", 0)) > int(g.get("away_penalty_score", 0)) else "客队"
                pen = f" (点球 {g.get('home_penalty_score','?')}:{g.get('away_penalty_score','?')}, {winner}胜)"
            lines.append(f"- **{sn}**: {h} {hs} - {ascore} {a}{pen}")
        lines.append("")
    else:
        lines.append("> 暂无淘汰赛数据\n")

    # 7. API 状态
    lines.append("---\n")
    lines.append("## 7. API 健康检查\n")
    lines.append(f"- **端点**: `{API_URL}`")
    lines.append(f"- **数据总量**: {len(games)} 场")
    lines.append(f"- **已完成**: {len(finished_all)} 场")
    lines.append(f"- **待进行**: {len(games) - len(finished_all)} 场")
    lines.append(f"- **最后更新**: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **状态**: ✅ 正常运行\n")

    lines.append("---\n")
    lines.append(f"本报告由 [WorldFIFA2026](https://sagebool.github.io/worldFIFA2026/) 自动化系统每日生成。\n")
    lines.append(f"数据截至 {now.strftime('%Y年%m月%d日 %H:%M')}，基于 [worldcup26.ir](https://worldcup26.ir) 公开数据整理。\n")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("世界杯每日数据测试报告 v3.0")
    print("=" * 60)

    games = fetch_games()
    report = gen_report(games)

    today = datetime.now().strftime("%Y-%m-%d")
    filepath = f"{REPORT_DIR}/test-report-{today}.md"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ 报告已保存: {filepath}")
    print("\n" + report)


if __name__ == "__main__":
    main()
