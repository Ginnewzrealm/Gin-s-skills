#!/usr/bin/env python3
"""计算 PDCA 周号（周日起点算法，禁止 ISO 8601）。

周起点 = 周日 00:00:00 CST，周终点 = 周六 23:59:59 CST。
每年第一个周日 = 当年 Week 1 的第 1 天，之后每 7 天累加。

用法：
    python3 week_number.py            # 使用今天（本地时间）
    python3 week_number.py 2026-07-12 # 指定日期
输出：JSON，含 year / weekNumber / dayOfWeek / weekLabel
"""
import json
import sys
from datetime import date, datetime


def get_week_number(d: date) -> dict:
    year = d.year
    jan1 = date(year, 1, 1)
    # date.weekday(): 周一=0 ... 周日=6
    days_to_first_sunday = (6 - jan1.weekday()) % 7
    first_sunday = date(year, 1, 1 + days_to_first_sunday)
    diff_days = (d - first_sunday).days

    if diff_days < 0:
        # 归入上一年：以上一年第一个周日为基准重新计算
        # （不能递归返回 12 月 31 日的结果——那会丢失目标日期与年末的天数差）
        prev_year = year - 1
        jan1_prev = date(prev_year, 1, 1)
        first_sunday_prev = date(prev_year, 1, 1 + (6 - jan1_prev.weekday()) % 7)
        diff_days = (d - first_sunday_prev).days
        year = prev_year

    week_number = diff_days // 7 + 1
    day_of_week = diff_days % 7 + 1  # 周日=1，周一=2，...，周六=7
    return {
        "year": year,
        "weekNumber": week_number,
        "dayOfWeek": day_of_week,
        "weekLabel": f"{year}-W{week_number:02d}",
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    else:
        target = date.today()
    print(json.dumps(get_week_number(target), ensure_ascii=False))
