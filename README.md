# KTTP Research v0.1 Alpha

本版本只完成第一阶段：

- 连接本机已登录的 MT5
- 自动识别 XAUUSDM / XAUUSD / GOLD
- 同步 M1、M5、M15、H1、D1 历史K线
- 保存到 SQLite 数据库
- 显示每个周期的同步数量、日期范围和状态

本版本不做回测、不扫描交易信号、不下单。

## 安装

1. 保持 TMGM MT5 打开并登录。
2. 双击 `install_windows.bat`。
3. 安装完成后双击 `run_windows.bat`。
4. 点击软件中的“连接 MT5”。
5. 点击“同步历史数据”。

## 数据位置

数据库保存在：

`data/kttp_research.db`

## 安全边界

项目没有任何下单、改单、平仓或持仓管理代码。
