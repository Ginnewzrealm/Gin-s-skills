#!/bin/bash
# 全技能测试入口：逐个技能目录运行 pytest（各技能 tests/ 无包结构，
# 跨目录同名测试模块会撞名，故按目录隔离运行）。
cd "$(dirname "$0")" || exit 1
total=0; failed=0; failed_dirs=""
for d in collector gin-fitness-pdca gin-fitness-tracker gin-problem-clarify gin-question \
         gin-resume-builder gin-story-architect gin-tutorial-harvest gin-tutorial-source-scan \
         gin-wechat-article-angle gin-wechat-article-clarify gin-wechat-article-core \
         gin-wechat-article-outline gin-wechat-article-polish gin-wechat-article-quality \
         gin-wechat-article-title gin-wechat-article-writer gin-workout-planner \
         gin-writing-materials huanyuan-liucheng opencli-chrome-launcher xiejiaocheng; do
  [ -d "$d/tests" ] || continue
  if out=$(python3 -m pytest "$d" -q --tb=short -p no:cacheprovider 2>&1); then
    summary=$(printf '%s\n' "$out" | tail -1)
    echo "ok   $d: $summary"
  else
    failed=$((failed + 1)); failed_dirs="$failed_dirs $d"
    summary=$(printf '%s\n' "$out" | tail -1)
    echo "FAIL $d: $out"
  fi
  n=$(echo "$summary" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+")
  total=$((total + ${n:-0}))
done
echo "=== 合计 $total passed, $failed 个技能目录失败$failed_dirs ==="
[ "$failed" -eq 0 ]
