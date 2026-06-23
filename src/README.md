# 📸 照片隐形足迹曝光器

> **Photo Privacy Invisible Footprint Exposer** — 一款基于 Streamlit 的交互式 Web 应用，用于演示数字照片中隐藏的 EXIF 元数据及其潜在隐私风险。

---

## 项目简介

当你在社交平台发送一张「看似普通」的照片时，这张图片里可能悄悄携带着**拍摄时间、设备型号，乃至精确的 GPS 地理坐标**。这些信息以 EXIF（Exchangeable Image File Format）元数据的形式嵌入在 JPEG / TIFF 文件中，对普通用户完全不可见，却可被专门工具一键读取。

**照片隐形足迹曝光器**正是为此而设计：

| 功能模块 | 说明 |
|---------|------|
| **元数据解析** | 自动提取拍摄时间（`DateTimeOriginal`）、设备品牌（`Make`）与型号（`Model`） |
| **GPS 坐标还原** | 将 EXIF 中度分秒（DMS）格式的经纬度转换为十进制小数，并在交互地图上精准标注 |
| **隐私安全提示** | 对经微信等渠道压缩、已剥离 EXIF 的图片，友好提示「未包含位置隐私信息」 |

本项目为**计算机相关课程期末演示项目**，旨在提高公众对「数字足迹」与「位置隐私」的认知，**请勿用于未经授权的图片分析**。

---

## 核心技术栈

| 技术 | 角色 |
|------|------|
| **Python 3.9+** | 项目主语言，负责 EXIF 解析与业务逻辑 |
| **Streamlit** | 快速构建交互式 Web 界面，零前端代码 |
| **Pillow (PIL)** | 读取图片二进制流，解析 EXIF / GPS 标签 |
| **Folium** | 基于 Leaflet.js 生成交互式 OpenStreetMap 地图 |
| **streamlit-folium** | 将 Folium 地图无缝嵌入 Streamlit 页面 |

### GPS 坐标转换算法

EXIF 标准将经纬度存储为 **度（D）· 分（M）· 秒（S）** 的有理数元组。本项目的核心转换公式为：

```
Decimal Degrees = D + (M / 60) + (S / 3600)
```

并根据参考方向修正符号：

- `GPSLatitudeRef = "S"`（南纬）→ 纬度 × (−1)
- `GPSLongitudeRef = "W"`（西经）→ 经度 × (−1)

---

## 如何运行本项目

### 方式一：桌面版（推荐，双击即用）

项目已提供 **Windows 桌面独立程序**，无需安装 Python、无需打开命令行、无需启动浏览器服务。

1. 在桌面找到 **`照片隐形足迹曝光器.exe`**
2. **双击**即可打开应用窗口
3. 点击「选择照片」，上传 JPG / JPEG / TIFF 原图即可分析

> 首次启动可能需等待数秒（程序在解压内置运行环境）。地图功能需要联网加载 OpenStreetMap 瓦片。

如需重新打包桌面版，在项目目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File build_desktop.ps1
```

### 方式二：Streamlit 网页版（开发调试）

确保本机已安装 **Python 3.9 或更高版本**。可通过以下命令验证：

```bash
python --version
```

### 第一步：克隆或下载项目

将项目文件夹放置到本地任意目录，例如：

```
AIask/
├── app.py
├── requirements.txt
└── README.md
```

### 第二步：创建虚拟环境（推荐）

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 第三步：安装依赖

```bash
pip install -r requirements.txt
```

### 第四步：启动应用

```bash
streamlit run app.py
```

启动成功后，终端将输出本地访问地址（默认为 `http://localhost:8501`），浏览器会自动打开应用页面。

### 使用说明

1. 点击页面上方的文件上传区域，选择一张 **JPG / JPEG / TIFF** 格式的照片；
2. 若照片包含完整 EXIF 数据，左侧将展示拍摄时间与设备信息，右侧显示原图预览，底部地图将标注拍摄地点；
3. 若照片经社交平台压缩（如微信转发），通常已剥离 GPS 信息，页面将提示「没有包含位置隐私信息」——这恰恰说明安全处理是有效的。

> **测试建议**：使用手机相机**原图模式**直接拍摄并上传（勿经微信转发），可观察到完整的 GPS 标注效果。

---

## 项目结构

```
AIask/
├── desktop_app.py          # 桌面版主程序（Tkinter）
├── app.py                  # Streamlit 网页版（可选）
├── desktop_requirements.txt
├── build_desktop.ps1       # 一键打包脚本
├── requirements.txt
└── README.md
```

---

## 隐私与伦理声明

- 本项目**仅用于教学演示**，帮助理解数字照片中的元数据风险；
- 上传的图片仅在本地浏览器会话中处理，**不会上传至任何外部服务器**；
- 请勿将本工具用于分析他人照片或任何未经授权的用途；
- 发送照片前，建议关闭手机相机的「位置信息」选项，或使用图片编辑工具清除 EXIF 数据。

---

## 许可证

本项目仅供学习与期末答辩展示使用。
