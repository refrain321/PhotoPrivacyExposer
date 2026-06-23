# 📸 照片隐形足迹曝光器 — Photo Privacy Exposer

> **看得见的照片，看不见的足迹。** 一款用于演示数字照片中隐藏的 EXIF 元数据及 GPS 位置隐私风险的桌面工具。

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python" />
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey.svg" alt="Platform" />
  <img src="https://img.shields.io/badge/license-Educational-green.svg" alt="License" />
</p>

---

## 🧐 这是什么？

当你在社交平台发送一张"普通"照片时，它可能悄悄携带了**拍摄时间、设备型号，乃至精确到米级的 GPS 地理坐标**。这些 EXIF 元数据对普通用户完全不可见，却可被专用工具一键读取。

**照片隐形足迹曝光器**能从照片中提取这些隐藏信息，并在交互式地图上精准还原拍摄地点——让你直观感受"数字足迹"的存在。

| 功能 | 说明 |
|------|------|
| 🔍 **元数据解析** | 自动提取拍摄时间（`DateTimeOriginal`）、设备品牌（`Make`）与型号（`Model`） |
| 🗺️ **GPS 坐标还原** | 将 EXIF 中度分秒（DMS）经纬度转为十进制，在 Leaflet 交互地图上精准标注 |
| 🛡️ **隐私安全提示** | 对已剥离 EXIF 的照片友好提示，帮助用户理解安全处理的重要性 |
| 🖥️ **桌面原生体验** | 基于 pywebview + Leaflet.js，丝滑地图支持拖动、缩放，无需浏览器 |

---

## 📸 界面预览

> 运行截图：左侧显示元数据，右侧预览原图，底部交互地图标注 GPS 拍摄位置。

```
┌─────────────────────────────────────────────────┐
│  📸 照片隐形足迹曝光器                            │
│  ⚠ 本项目仅用于期末演示...                        │
├────────────────────┬────────────────────────────┤
│  提取的元数据        │  原图预览                    │
│  拍摄时间: 2024...   │  ┌──────────────────┐      │
│  设备型号: Apple...  │  │                  │      │
│  纬度: 31.230416    │  │    📷 照片       │      │
│  经度: 121.473701   │  │                  │      │
│                    │  └──────────────────┘      │
├────────────────────┴────────────────────────────┤
│  拍摄位置地图                                     │
│  ┌──────────────────────────────────────────┐  │
│  │         🗺️  Leaflet 交互地图              │  │
│  │              📍 拍摄地                    │  │
│  │                                          │  │
│  └──────────────────────────────────────────┘  │
│  [打开 Google 地图] [打开 OpenStreetMap]         │
└─────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 方式一：下载 EXE 直接运行（推荐）

1. 前往 [Releases](../../releases) 页面
2. 下载 `PhotoPrivacyExposer_SMOOTH_MAP.exe`（约 64 MB）
3. **双击运行**，无需安装 Python 或任何依赖

> 首次启动需等待数秒（解压内置运行环境）。地图功能需要联网加载 OpenStreetMap 瓦片。

### 方式二：从源码运行

**环境要求：** Python 3.9+

```bash
# 克隆仓库
git clone https://github.com/refrain321/PhotoPrivacyExposer.git
cd PhotoPrivacyExposer/src

# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate   # Windows

# 安装依赖
pip install -r desktop_requirements.txt
pip install pywebview

# 启动桌面应用（丝滑地图版）
python desktop_webview_app.py
```

你也可以运行 Streamlit 网页版（用于开发调试）：

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 🧱 项目结构

```
PhotoPrivacyExposer/
├── src/
│   ├── desktop_webview_app.py   # 桌面版主程序（pywebview + Leaflet，推荐）
│   ├── desktop_app.py           # 旧版 Tkinter 桌面程序
│   ├── app.py                   # Streamlit 网页版
│   ├── build_desktop.ps1        # 一键打包脚本
│   ├── requirements.txt         # Streamlit 版依赖
│   └── desktop_requirements.txt # 桌面版依赖
├── test_images/                 # 测试用照片（含 GPS / 无 GPS）
├── .gitignore
└── README.md
```

---

## 🔬 核心技术

| 技术 | 角色 |
|------|------|
| **Python 3.9+** | 项目主语言，EXIF 解析与业务逻辑 |
| **Pillow (PIL)** | 读取图片二进制流，解析 EXIF / GPS IFD 标签 |
| **pywebview** | 将 HTML5 前端嵌入原生桌面窗口 |
| **Leaflet.js** | 交互式 OpenStreetMap 地图，支持拖动、缩放 |
| **Streamlit + Folium** | （网页版）快速构建 Web 界面与地图 |

### GPS 坐标转换原理

EXIF 标准将经纬度存储为 **度° 分′ 秒″** 的有理数元组：

```
Decimal Degrees = D + (M / 60) + (S / 3600)
```

并根据参考方向修正符号（南纬 S / 西经 W 为负值）。

---

## ⚠️ 隐私与伦理声明

- 📚 本项目**仅用于教学演示**，帮助理解数字照片的元数据风险
- 🔒 所有图片处理**完全在本地进行**，不会上传至任何外部服务器
- ❌ **请勿**将本工具用于分析他人照片或任何未经授权的用途
- 💡 发送照片前，建议关闭手机相机的「记录位置信息」选项，或使用图片工具清除 EXIF

---

## 📝 License

本项目仅供学习与教学演示使用。测试照片来源于公开 EXIF 样本数据集。

---

<p align="center">
  <sub>Made with ❤️ for privacy awareness | 期末演示项目</sub>
</p>
