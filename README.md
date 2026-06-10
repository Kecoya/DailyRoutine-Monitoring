<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="MIT License">
  <img src="https://img.shields.io/badge/Version-1.3.0-blue?style=flat-square" alt="Version">
</p>

<h1 align="center">📊 DailyRoutine Monitoring</h1>

<p align="center">
  <strong>研究生 / 科研工作者桌面作息追踪与工作量分析系统</strong><br>
  实时监控 · 数据分析 · 作息追踪 · 摄像头抓拍 · 隐私安全
</p>

---

## 📖 项目简介

**DailyRoutine Monitoring** 是一款运行在 Windows 桌面的轻量级作息追踪与工作量分析工具。程序以后台服务形式运行，通过监控鼠标、键盘、窗口和系统活动，自动生成忙碌指数、工作达成率、专注度等多维度分析报告，并通过美观的 Web 界面可视化呈现。同时支持定时摄像头抓拍，自动记录工作场景。

**适用场景：**
- 📚 研究生 / 科研工作者追踪每日实验室坐班时长
- 💼 自由职业者量化工作投入
- 🧠 任何希望了解自己"时间都去哪了"的人

**核心原则：所有数据仅存储于本地 SQLite 数据库，不上传任何服务器。**

---

## ✨ 功能特性

### 实时监控
- 🔧 **开机自启动**：支持 Windows 开机静默启动，无感知后台运行
- 🖱️ **鼠标追踪**：实时记录移动距离、点击次数、移动频率
- ⌨️ **键盘追踪**：记录按键频率（不记录按键内容）
- 🪟 **窗口追踪**：记录窗口切换次数和活动窗口标题
- 💻 **系统监控**：CPU / 内存使用率采集

### 智能分析
- 📊 **忙碌指数 (0-100)**：加权融合鼠标、键盘、窗口、系统四维指标
- 🎯 **工作达成率**：当日实际活动时长 vs 自定义标准工时
- 🔥 **工作强度**：综合时长 × 忙碌度的投入评估
- 🧘 **专注度评分**：基于窗口切换频率，越高代表越专注
- ⚡ **效率指数**：单位时间内的操作活跃度
- 📅 **作息规律性**：基于每日开机时间标准差

### 可视化报表
- 📈 **忙碌度曲线**：精确到分钟的全天活动曲线（含次日凌晨 2 点前数据）
- 🗓️ **活动日历**：月度日历热力图，一目了然查看每日工作量
- 📉 **趋势图表**：任意时间段的活动时长和忙碌指数趋势
- 📋 **周报 / 月报**：自动统计工作天数、日均时长、综合指标
- 🔍 **自定义分析**：自由选择任意时间段进行深入分析

### 数据导出
- 📥 **CSV 导出**：原始数据，方便 Python / Excel 进一步分析
- 📥 **Excel 导出**：含每日明细 + 汇总统计双工作表

### 📷 摄像头抓拍（v1.3.0 新增）
- 🎥 **时间段抓拍**：配置多个每日时间段，按指定间隔（如每 60 秒）自动拍照
- 📌 **固定时间抓拍**：在每天特定时间点（如 08:50、14:50、19:50）永久拍照
- 🎞️ **GIF 动图**：每个时间段结束时自动将临时照片合成为 GIF 动图
- 🏷️ **时间戳水印**：每张照片自动叠加拍摄时间
- 🧹 **自动清理**：过期临时照片自动删除，GIF 和永久照片长期保存
- 🖥️ **Web 查看**：在 Web 界面中浏览临时抓拍、永久抓拍和 GIF 动图
- 🔒 **隐私安全**：摄像头按需初始化、空闲自动释放，照片仅存本地

### 隐私与安全
- 🔒 所有数据存储于本地 `data/activity.db`（SQLite）
- 🔒 不记录键盘输入内容，仅统计按键次数
- 🔒 不截屏、不录音、不联网上传
- 🔒 摄像头照片仅存储于本地，可通过配置禁用抓拍功能
- 🔒 支持自定义数据保留天数，过期自动清理

---

## 🖼️ 界面预览

<details>
<summary>点击展开 Web 界面截图描述</summary>

### 今日概览
- 六宫格数据卡片：活动时长、工作达成率、鼠标点击、键盘按键、鼠标移动距离、平均忙碌指数
- 忙碌度曲线图：0-26 小时全时段，红色标注空闲时段

### 本周报表
- 统计周期概览：总天数、有效工作天数、排除天数说明
- 综合指标：日均活动时长、鼠标移动距离、工作强度、专注度、效率指数、作息规律性
- 双子图趋势：活动时长 + 忙碌指数，含平均值线和标准工时参考线

### 本月报表
- 月度日历热力图：每个日期格子显示活动时长和工作达成率
- 统计汇总表格

### 自定义分析
- 自由选择起止日期
- 趋势图 + 完整统计报表

### 数据导出
- CSV / Excel 双格式支持
- Excel 包含"每日统计"和"汇总统计"两个工作表

### 摄像头抓拍
- 服务状态卡片：抓拍运行状态、摄像头连接状态、活跃线程数
- 图片网格：浏览临时抓拍、永久抓拍和 GIF 动图
- 点击图片可查看大图

</details>

---

## 🚀 快速开始

### 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 / 11 |
| Python | 3.8 或更高版本 |
| 磁盘空间 | ≥ 100 MB |

### 安装

```bash
# 克隆仓库
git clone https://github.com/Kecoya/DailyRoutine-Monitoring.git
cd DailyRoutine-Monitoring

# 安装依赖
pip install -r requirements.txt
```

### 启动

```bash
python main.py
```

启动后打开浏览器访问 **http://127.0.0.1:5000** 即可查看 Web 界面。

### 设置开机自启动

```bash
python setup_autostart.py
```

选择选项 `1` 即可在 Windows 启动文件夹中创建快捷方式，下次开机自动静默运行。

> 📖 更详细的安装和配置指南请参考 [INSTALL.md](INSTALL.md)

---

## 🏗️ 项目结构

```
DailyRoutine-Monitoring/
├── main.py                 # 程序入口（含单实例检测、stdio 修复）
├── config.py               # 全局配置文件
├── monitor_service.py      # 核心监控服务（双缓冲计数器，pynput 零阻塞回调）
├── camera_service.py       # 摄像头抓拍服务（时间段抓拍 + 固定时间抓拍 + GIF 生成）
├── database.py             # 数据库访问层（SQLite WAL 模式）
├── analyzer.py             # 数据分析模块（统计 + 图表生成）
├── web_app.py              # Flask Web 服务器
├── silent_launcher.py      # 静默启动器（用于开机自启，无窗口）
├── setup_autostart.py      # 自启动配置工具
├── requirements.txt        # Python 依赖列表
├── restart.bat             # 安全重启脚本
├── 启动监控.bat             # 一键启动（双击运行）
├── 安装依赖.bat             # 一键安装依赖
├── templates/
│   └── index.html          # Web 前端页面
├── static/                 # 运行时生成的图表（自动清理）
├── data/                   # 数据库文件（.gitignore 排除）
│   └── captures/           # 摄像头抓拍数据（.gitignore 排除）
└── logs/                   # 日志文件（.gitignore 排除）
```

---

## ⚙️ 配置说明

所有配置项集中在 `config.py` 中，可根据个人需求自由调整：

```python
# ===== 监控配置 =====
MONITOR_INTERVAL = 60       # 数据保存间隔（秒），越小精度越高，数据量越大
IDLE_THRESHOLD = 600        # 空闲判定阈值（秒），10 分钟无活动视为空闲
NAP_TIME_START = 13         # 午休开始时间（小时）
NAP_TIME_END = 14.5         # 午休结束时间（小时）

# ===== Web 服务 =====
WEB_HOST = '127.0.0.1'      # 绑定地址（默认仅本机访问）
WEB_PORT = 5000             # 端口号

# ===== 忙碌度计算权重 =====
BUSY_WEIGHTS = {
    'mouse_activity': 0.30,    # 鼠标活动权重
    'keyboard_activity': 0.30, # 键盘活动权重
    'window_switches': 0.20,   # 窗口切换权重
    'system_usage': 0.20       # 系统资源权重
}

# ===== 个人化设置 =====
LAB_WORK_HOURS = 8.5        # 每日标准工作时长（小时），用于计算工作达成率
PIXELS_PER_METER = 5200     # 鼠标距离换算系数，根据显示器调整
DATA_RETENTION_DAYS = 365   # 数据保留天数

# ===== 摄像头抓拍配置 =====
CAPTURE_ENABLED = True              # 是否启用摄像头抓拍（设为 False 可完全禁用）
CAPTURE_CAMERA_ID = 0               # 摄像头设备 ID
CAPTURE_TIME_RANGES = [             # 时间段抓拍（保存为临时文件，结束时生成 GIF）
    {"start": "11:30", "end": "14:30", "interval": 60},
    {"start": "17:30", "end": "18:30", "interval": 60},
    {"start": "21:30", "end": "23:59", "interval": 60},
]
CAPTURE_FIXED_TIMES = [             # 固定时间点抓拍（永久保存）
    {"time": "08:50", "description": "morning"},
    {"time": "14:50", "description": "noon"},
    {"time": "19:50", "description": "night"},
]
CAPTURE_GIF_FPS = 24                # GIF 帧率
CAPTURE_CLEANUP_DAYS = 7            # 临时照片保留天数
CAPTURE_TIMESTAMP_ENABLED = True    # 是否在照片上添加时间戳水印
```

### 关于 `MONITOR_INTERVAL`

| 间隔 | 日数据量 | 年数据量 | 适用场景 |
|------|---------|---------|---------|
| 5 秒 | ~3.4 MB | ~1.2 GB | 高精度分析 |
| 30 秒 | ~570 KB | ~200 MB | 均衡 |
| **60 秒** | **~280 KB** | **~100 MB** | **推荐默认** |
| 120 秒 | ~140 KB | ~50 MB | 低配设备 |

> 活动指标的计算已自动适配不同间隔（`interval_factor`），无需手动调整其他参数。

### 关于 `PIXELS_PER_METER`

基于典型显示器物理尺寸的经验换算值：

| 显示器 | 分辨率 | 参考值 |
|--------|--------|--------|
| 24 寸 FHD | 1920×1080 | ~3600 |
| 27 寸 FHD | 1920×1080 | ~3200 |
| 27 寸 2K | 2560×1440 | ~4300 |
| 32 寸 4K | 3840×2160 | ~5500 |

可根据实际显示器测量值调整，计算方法：`水平分辨率 ÷ (屏幕宽度cm ÷ 100)`。

---

## 🧮 算法说明

### 忙碌指数

忙碌指数通过四维指标加权计算，范围 0-100：

```
BusyIndex = mouse_score × 0.30 + keyboard_score × 0.30
          + window_score × 0.20 + system_score × 0.20
```

每个子指标的归一化参考值（每分钟基准）：
- 鼠标移动：5000 px → 50 分，点击：50 次 → 30 分，移动次数：500 → 20 分
- 键盘按键：300 次 → 100 分
- 窗口切换：10 次 → 100 分
- 系统占用：(CPU% + Memory%) / 2

当用户空闲时间超过阈值（默认 10 分钟）时，忙碌指数强制归零。

### 综合评估指标

| 指标 | 公式 | 含义 |
|------|------|------|
| 工作强度 | (活动时长 × 忙碌指数) / 平均活动时长 | 综合投入程度 |
| 专注度 | 100 - (窗口切换次数 / 活动小时数) | 分数越高越专注 |
| 效率指数 | (鼠标点击 + 键盘按键) / 活动分钟数 | 操作活跃度 |
| 规律性 | max(0, 100 - 开机时间标准差 × 10) | 作息稳定程度 |
| 达成率 | 实际活动时长 / 标准工时 × 100% | 当日目标完成度 |

### 跨日处理

工作日的统计范围定义为 **当天 00:00 ~ 次日 02:00**，凌晨 0-2 点的活动自动归入前一天的统计，确保加班到凌晨的工作量不会丢失。

---

## 🔒 隐私设计

本系统在设计上最大程度保护用户隐私：

| 维度 | 说明 |
|------|------|
| **数据存储** | 仅使用本地 SQLite，无网络连接 |
| **键盘监控** | 仅记录按键次数，不记录按键内容 |
| **鼠标监控** | 仅记录移动距离和点击次数，不记录屏幕坐标 |
| **窗口标题** | 记录活动窗口标题用于分析，可选择性禁用 |
| **摄像头抓拍** | 摄像头按需初始化、空闲自动释放，照片仅存本地，可配置禁用 |
| **数据清理** | 支持自定义保留天数，过期数据自动清除 |
| **数据导出** | 所有数据可导出为 CSV/Excel，用户完全掌控 |

---

## 🛠️ 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.8+ |
| Web 框架 | Flask |
| 数据库 | SQLite (WAL 模式) |
| 系统监控 | psutil, pynput, pywin32 (win32gui) |
| 摄像头抓拍 | opencv-python, schedule, Pillow |
| 数据分析 | pandas, numpy |
| 可视化 | matplotlib, seaborn |
| 数据导出 | openpyxl |
| 前端 | 原生 HTML/CSS/JS（无框架依赖） |

---

## 📋 依赖列表

```
Flask          # Web 服务器
psutil         # 系统资源监控
pynput         # 鼠标/键盘事件监听
pywin32        # Windows API（窗口管理、快捷方式）
matplotlib     # 图表生成
pandas         # 数据分析
numpy          # 数值计算
seaborn        # 统计可视化
openpyxl       # Excel 导出
opencv-python  # 摄像头抓拍
schedule       # 定时任务调度
Pillow         # GIF 动图生成
```

---

## ❓ 常见问题

<details>
<summary><strong>程序提示"已在运行中"怎么办？</strong></summary>

这是内置的单实例检测机制，说明已有监控进程在后台运行。如果需要重启，请使用 `restart.bat` 或手动结束进程后重新启动。
</details>

<details>
<summary><strong>Web 界面打不开？</strong></summary>

1. 确认程序正在运行（检查任务管理器中的 python/pythonw 进程）
2. 尝试访问 `http://127.0.0.1:5000`（不是 localhost）
3. 检查端口 5000 是否被其他程序占用
4. 查看日志文件 `logs/monitor.log` 获取错误信息
</details>

<details>
<summary><strong>开机自启动不生效？</strong></summary>

1. 运行 `python setup_autostart.py` 选择选项 `3` 检查状态
2. 按 `Win+R` 输入 `shell:startup` 确认快捷方式是否存在
3. 查看 `logs/silent_launcher.log` 确认启动是否成功
</details>

<details>
<summary><strong>鼠标移动距离不准？</strong></summary>

`PIXELS_PER_METER` 的默认值基于 24 寸 1920×1080 显示器。如果你的显示器规格不同，请根据实际物理尺寸调整此值。计算方法见 [配置说明](#️-配置说明) 章节。
</details>

<details>
<summary><strong>如何彻底卸载？</strong></summary>

1. 运行 `python setup_autostart.py` → 选择 `2` 移除自启动
2. 关闭正在运行的程序（Ctrl+C 或任务管理器结束进程）
3. 删除项目文件夹
</details>

---

## 🗺️ 开发路线

- [x] 实时监控（鼠标/键盘/窗口/系统）
- [x] Web 可视化界面
- [x] 忙碌度曲线图 + 日历热力图 + 趋势图
- [x] 周报/月报/自定义分析
- [x] CSV/Excel 数据导出
- [x] 开机自启动（静默运行）
- [x] 单实例检测（防止多开）
- [x] 线程安全（双缓冲计数器 + 图表生成锁）
- [x] 摄像头定时抓拍（时间段抓拍 + 固定时间抓拍 + GIF 生成）
- [ ] 应用程序使用时长统计
- [ ] 系统托盘图标 + 右键菜单
- [ ] 多显示器支持
- [ ] 自定义忙碌度计算规则
- [ ] 移动端响应式适配
- [ ] 数据备份与恢复功能

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

<p align="center">
  Made with ❤️ for researchers who want to track their daily routines.
</p>
