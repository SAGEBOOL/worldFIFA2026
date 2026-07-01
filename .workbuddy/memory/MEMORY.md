# worldFIFA2026 项目长期记忆

## 项目定位
2026 世界杯球迷宣传站 / 数据展示 + 点球小游戏（轻量 HTML 单页应用）

## 关键技术栈
- 纯静态 HTML（单文件，无构建）
- 数据源：worldcup26.ir API（v1.0.5，REST 风格）
- 部署：GitHub Pages（main 分支根目录 + GitHub Actions）
- 仓库：https://github.com/SAGEBOOL/worldFIFA2026
- 公网地址：https://sagebool.github.io/worldFIFA2026/

## 工作流程约定
- **修改 → 推送**：`git add -A && git commit -m "..." && git push --force origin main`
- **强制推送**：清空重建时用 `--force`
- **MD5 校验**：用 `md5sum` 验证文件同步一致性
- **部署入口**：`workbuddy_cloudstudio_deploy` 部署到 CloudStudio 沙箱（仅预览用）

## 数据 API（worldcup26.ir）
- 主接口：`/get/games` 返回所有比赛数据
- 字段：home_team_name_en / away_team_name_en / home_score / away_score / finished / local_date / type
- 日期格式：MM/DD/YYYY（注意非 ISO 格式）

## 自动化任务
- 名称：世界杯每日数据报告推送
- ID：automation-1782700617890
- 频率：每天 4:00、7:00、12:00、16:00（北京时间）
- 输出：test-report-YYYY-MM-DD.md + index.html 自动更新
- 数据截至：2026年7月1日（R32 6场已完成）

## 用户偏好
- 文件命名严格一致（如 `test-report-YYYY-MM-DD.md`）
- 避免冗余修辞，直接给结论
- 高风险操作（清空、删除）必须明确确认
- Web 项目偏好单文件 HTML + 外部浏览器可访问

## 经验教训
- Wikimedia Commons 在沙箱中无法访问，但用户浏览器可以正常访问
- GitHub Pages 启用后部署类型选择 "GitHub Actions" 避免 Jekyll 干扰
- 用户经常说"确认清空"时要二次确认，因为是不可逆操作
