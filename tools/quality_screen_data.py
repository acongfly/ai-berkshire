#!/usr/bin/env python3
"""去劣筛选数据取数器 — 为 skills/quality-screen.md 的 7 条指标批量取数。

补齐 ashare_data.py 未覆盖的字段：毛利率、净利率、利息覆盖倍数、
经营现金流/净利润、自由现金流、总股本膨胀率、以及银行专属指标。

数据源：东方财富 datacenter API（F10 主要财务指标 + 现金流量表），零外部依赖。

用法：
    python3 tools/quality_screen_data.py 600036 601088 600941   # 逐个体检
    python3 tools/quality_screen_data.py --table 600036 601088  # 汇总表格
    python3 tools/quality_screen_data.py --json 600036          # JSON 输出

指标口径见 skills/quality-screen.md。
"""

import argparse
import json
import subprocess
import sys
from urllib.parse import quote

_TIMEOUT = 25
_YEARS = 10

MAIN_API = "https://datacenter.eastmoney.com/securities/api/data/get"
CF_API = "https://datacenter.eastmoney.com/securities/api/data/v1/get"


def _curl_json(url):
    r = subprocess.run(
        ["/usr/bin/curl", "-s", "--noproxy", "*",
         "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", url],
        capture_output=True, timeout=_TIMEOUT,
    )
    if r.returncode != 0 or not r.stdout.strip():
        raise ConnectionError(f"请求失败: {url[:80]}")
    return json.loads(r.stdout.decode("utf-8", errors="replace"))


def _secucode(code):
    code = code.strip().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
    mkt = "SH" if code.startswith(("6", "9", "5")) else "SZ"
    return f"{code}.{mkt}", code


def fetch_main(code, years=_YEARS):
    """F10 主要财务指标，近 N 年年报。"""
    secucode, _ = _secucode(code)
    flt = quote(f'(SECUCODE="{secucode}")(REPORT_TYPE="年报")')
    url = (f"{MAIN_API}?type=RPT_F10_FINANCE_MAINFINADATA&sty=ALL&filter={flt}"
           f"&p=1&ps={years}&sr=-1&st=REPORT_DATE&source=HSF10&client=PC")
    return (_curl_json(url).get("result") or {}).get("data") or []


def fetch_cashflow(code, years=_YEARS):
    """现金流量表，仅保留年报（12-31）。"""
    secucode, _ = _secucode(code)
    flt = quote(f'(SECUCODE="{secucode}")')
    url = (f"{CF_API}?reportName=RPT_F10_FINANCE_GCASHFLOW&columns=ALL&filter={flt}"
           f"&pageNumber=1&pageSize={years * 5}&sortColumns=REPORT_DATE&sortTypes=-1"
           f"&source=HSF10&client=PC")
    rows = (_curl_json(url).get("result") or {}).get("data") or []
    return [r for r in rows if str(r.get("REPORT_DATE", "")).startswith(tuple(str(y) for y in range(2010, 2031)))
            and "-12-31" in str(r.get("REPORT_DATE", ""))]


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def analyze(code):
    main = fetch_main(code)
    if not main:
        return {"code": code, "error": "未取到主要财务指标"}
    try:
        cf = fetch_cashflow(code)
    except Exception:
        cf = []

    name = main[0].get("SECURITY_NAME_ABBR", code)
    org_type = main[0].get("ORG_TYPE", "")
    is_bank = org_type == "银行"

    years = [str(r.get("REPORT_YEAR")) for r in main]
    roe = [_f(r.get("ROEJQ")) for r in main]
    gross = [_f(r.get("XSMLL")) for r in main]
    netm = [_f(r.get("XSJLL")) for r in main]
    icr = [_f(r.get("INTSTCOVRATE")) or _f(r.get("INTEREST_COVERAGE_RATIO")) for r in main]
    ocf_np = [_f(r.get("NCO_NETPROFIT")) for r in main]
    ocf = [_f(r.get("NETCASH_OPERATE_PK")) for r in main]
    profit = [_f(r.get("PARENTNETPROFIT")) for r in main]
    eps = [_f(r.get("EPSJB")) for r in main]

    # TOTAL_SHARE 字段每年返回的都是「当前」股本（非历史值），无法用于测算稀释。
    # 改用 归母净利润 ÷ 基本EPS 反推加权平均股本 —— 该序列逐年真实变化。
    shares = []
    for p, e in zip(profit, eps):
        shares.append(p / e if (p is not None and e not in (None, 0)) else None)

    # 自由现金流 = 经营现金流 - 购建长期资产支付现金
    capex_by_year = {}
    for r in cf:
        y = str(r.get("REPORT_DATE", ""))[:4]
        capex_by_year[y] = _f(r.get("CONSTRUCT_LONG_ASSET"))
    fcf = []
    for i, y in enumerate(years):
        o, c = ocf[i] if i < len(ocf) else None, capex_by_year.get(y)
        fcf.append(o - c if (o is not None and c is not None) else None)

    n5 = 5
    fcf5 = [v for v in fcf[:n5] if v is not None]
    res = {
        "code": code, "name": name, "org_type": org_type, "is_bank": is_bank,
        "years": years,
        "roe_10y_avg": _avg(roe), "roe_series": roe,
        "gross_margin_avg": _avg(gross[:n5]), "gross_series": gross[:n5],
        "net_margin_avg": _avg(netm[:n5]), "net_margin_series": netm[:n5],
        "interest_coverage_min": min([v for v in icr[:n5] if v is not None], default=None),
        "icr_series": icr[:n5],
        "ocf_np_avg": _avg(ocf_np[:n5]), "ocf_np_series": ocf_np[:n5],
        "fcf_5y_sum": sum(fcf5) if fcf5 else None,
        "fcf_series": fcf[:n5],
        "fcf_years_covered": len(fcf5),
        "share_growth_5y": ((shares[0] / shares[min(4, len(shares) - 1)] - 1) * 100)
                            if shares and shares[0] and shares[min(4, len(shares) - 1)] else None,
        "shares_series": shares[:n5],
        "profit_series": profit[:n5],
        "total_share_now": _f(main[0].get("TOTAL_SHARE")),
    }
    # 投资控股型识别：营收极小、利润主要来自权益法投资收益时，
    # 毛利率/净利率/经营现金流三项口径失真，不能机械套用阈值。
    res["is_holding_co"] = bool(res["net_margin_avg"] and res["net_margin_avg"] > 100)
    if is_bank:
        r0 = main[0]
        res["bank"] = {
            "净息差": _f(r0.get("NET_INTEREST_MARGIN")),
            "净利差": _f(r0.get("NET_INTEREST_SPREAD")),
            "不良贷款率": _f(r0.get("NONPERLOAN")),
            "资本充足率": _f(r0.get("NEWCAPITALADER")),
            "一级资本充足率": _f(r0.get("FIRST_ADEQUACY_RATIO")),
            "拨贷比": _f(r0.get("LOAN_PROVISION_RATIO")),
            "净息差历年": [_f(r.get("NET_INTEREST_MARGIN")) for r in main[:n5]],
            "不良率历年": [_f(r.get("NONPERLOAN")) for r in main[:n5]],
        }
    return res


def verdict(a):
    """套用 quality-screen 7 条指标 + 3 条豁免。返回 (结论, 明细列表)。"""
    if a.get("error"):
        return "数据不足", [("—", a["error"], "⚠️")]
    rows, fails = [], []
    yi = 1e8

    def add(n, label, val, ok, txt):
        mark = "✅" if ok is True else ("❌" if ok is False else "⚠️")
        rows.append((f"{n}", f"{label}: {txt}", mark))
        if ok is False:
            fails.append(label)

    # 1 ROE
    v = a["roe_10y_avg"]
    add(1, "10年平均ROE", v, (v >= 8) if v is not None else None,
        f"{v:.2f}%" if v is not None else "无数据")
    # 2 FCF（银行不适用：存贷款流量会淹没经营现金流，FCF 无经济含义）
    v = a["fcf_5y_sum"]
    if a["is_bank"]:
        rows.append(("2", "自由现金流: 银行口径不适用（豁免）", "➖"))
    elif a.get("is_holding_co"):
        rows.append(("2", f"5年累计自由现金流 {v/yi:.0f}亿: 投资控股型，经营现金流不含"
                          f"被投企业分红（计入投资活动），口径失真（需人工判断）"
                     if v is not None else "自由现金流: 投资控股型，口径失真", "⚠️"))
    elif v is None:
        add(2, "5年累计自由现金流", v, None, "无数据")
    else:
        add(2, "5年累计自由现金流", v, v > 0,
            f"{v/yi:.0f}亿（覆盖{a['fcf_years_covered']}年）")
    # 3 利息覆盖（银行不适用）
    # 注意：本字段为负 = 财务费用净额为利息「收入」而非支出，即公司无利息负担，
    # 属于最安全的情形。机械取 min() 会把它误判为不及格，必须单独处理。
    if a["is_bank"]:
        rows.append(("3", "利息覆盖倍数: 银行不适用（豁免）", "➖"))
    else:
        pos = [v for v in a["icr_series"] if v is not None and v >= 0]
        neg = [v for v in a["icr_series"] if v is not None and v < 0]
        v = min(pos) if pos else None
        if neg and (v is None or v >= 2):
            rows.append(("3", f"利息覆盖倍数(5年最低): {v:.1f}倍；另有 {len(neg)} 年为负"
                              f"（=净利息收入，无利息负担，视为通过）"
                         if v is not None else
                         f"利息覆盖倍数: {len(neg)} 年均为净利息收入，无利息负担", "✅"))
        else:
            add(3, "利息覆盖倍数(5年最低)", v, (v >= 2) if v is not None else None,
                f"{v:.1f}倍" if v is not None else "无数据")
    # 4 毛利率
    v = a["gross_margin_avg"]
    if a["is_bank"]:
        rows.append(("4", "毛利率: 银行无此口径（豁免）", "➖"))
    elif a.get("is_holding_co"):
        rows.append(("4", f"毛利率 {v:.1f}%: 投资控股型，口径失真（需人工判断）"
                     if v is not None else "毛利率: 投资控股型，口径失真", "⚠️"))
    else:
        add(4, "长期毛利率", v, (v >= 15) if v is not None else None,
            f"{v:.2f}%" if v is not None else "无数据")
    # 5 经营现金流/净利润
    v = a["ocf_np_avg"]
    if a.get("is_holding_co"):
        rows.append(("5", f"经营现金流/净利润 {v:.2f}: 权益法投资收益为非现金利润，"
                          f"现金以被投企业分红形式流入投资活动，口径失真（需人工判断）"
                     if v is not None else "经营现金流/净利润: 口径失真", "⚠️"))
    else:
        add(5, "经营现金流/净利润(5年均值)", v, (v >= 0.7) if v is not None else None,
            f"{v:.2f}" if v is not None else "无数据")
    # 6 净利率
    v = a["net_margin_avg"]
    if a.get("is_holding_co"):
        rows.append(("6", f"净利率 {v:.0f}%: 营收仅为母公司口径，利润主要来自投资收益，"
                          f"该比率无经济含义", "⚠️"))
    else:
        add(6, "长期净利率", v, (v >= 5) if v is not None else None,
            f"{v:.2f}%" if v is not None else "无数据")
    # 7 股本膨胀
    v = a["share_growth_5y"]
    add(7, "5年总股本膨胀", v, (v <= 20) if v is not None else None,
        f"{v:+.2f}%" if v is not None else "无数据")

    # 豁免规则
    exempt = []
    gm, nm, roe_, ocfnp = (a["gross_margin_avg"], a["net_margin_avg"],
                           a["roe_10y_avg"], a["ocf_np_avg"])
    if "长期净利率" in fails and gm and gm > 30:
        nms = [x for x in a["net_margin_series"][:2] if x is not None]
        if nms and all(x >= 5 for x in nms):
            exempt.append("豁免B：毛利率>30%且近2年净利率已回升至5%以上")
            fails.remove("长期净利率")
    if roe_ and roe_ > 20 and ocfnp and ocfnp > 1.0:
        for f_ in ("长期毛利率", "长期净利率"):
            if f_ in fails:
                exempt.append(f"豁免C：ROE>20%且现金流质量>1.0，豁免「{f_}」")
                fails.remove(f_)

    detail = rows + [("豁免", e, "🔓") for e in exempt]
    if fails:
        concl = f"❌ 淘汰（触发 {len(fails)} 条）：{'、'.join(fails)}"
    else:
        # 口径失真的指标不能算「通过」——它只是没被机械判负，仍需人工核实
        n_warn = sum(1 for _, _, m in detail if m == "⚠️")
        concl = ("✅ 通过（进入深度研究）" if n_warn == 0
                 else f"⚠️ 需人工判断（{n_warn} 项指标口径失真，不构成通过）")
    return concl, detail


def main():
    p = argparse.ArgumentParser(description="去劣筛选批量取数")
    p.add_argument("codes", nargs="+")
    p.add_argument("--json", action="store_true")
    p.add_argument("--table", action="store_true")
    args = p.parse_args()

    results = []
    for c in args.codes:
        try:
            a = analyze(c)
        except Exception as e:
            a = {"code": c, "error": str(e)}
        a["verdict"], a["detail"] = verdict(a)
        results.append(a)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        return

    if args.table:
        hdr = f"{'标的':<12}{'ROE10y':>8}{'FCF5y亿':>10}{'利息覆盖':>9}{'毛利率':>8}{'OCF/NP':>8}{'净利率':>8}{'股本+%':>8}  结论"
        print(hdr); print("-" * len(hdr) * 2)
        for a in results:
            if a.get("error"):
                print(f"{a['code']:<12}  {a['error']}"); continue
            f = lambda v, s="{:.1f}": (s.format(v) if v is not None else "—")
            fcf_txt = "—" if a["fcf_5y_sum"] is None else "{:.0f}".format(a["fcf_5y_sum"] / 1e8)
            print(f"{a['name'][:11]:<12}{f(a['roe_10y_avg']):>8}{fcf_txt:>10}"
                  f"{f(a['interest_coverage_min']):>9}{f(a['gross_margin_avg']):>8}"
                  f"{f(a['ocf_np_avg'], '{:.2f}'):>8}{f(a['net_margin_avg']):>8}"
                  f"{f(a['share_growth_5y'], '{:+.1f}'):>8}  {a['verdict']}")
        return

    for a in results:
        print("=" * 66)
        print(f"{a.get('name', a['code'])} ({a['code']})  行业类型：{a.get('org_type', '—')}")
        print("=" * 66)
        for n, txt, mark in a["detail"]:
            print(f"  {mark} [{n}] {txt}")
        if a.get("bank"):
            print("  --- 银行专属指标（最新年报）---")
            for k, v in a["bank"].items():
                if isinstance(v, list):
                    print(f"      {k}: {['—' if x is None else round(x, 2) for x in v]}")
                else:
                    print(f"      {k}: {v}")
        print(f"\n  【结论】{a['verdict']}\n")


if __name__ == "__main__":
    main()
