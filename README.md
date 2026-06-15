# FishReader

一个轻量的透明 TXT 阅读小窗。适合快速打开小说文本、调节背景/文字透明度、隐藏工具栏，并用快捷键一键最小化。

> 项目定位：轻量、快速启动、功能只保留阅读时真正需要的部分。
<img width="464" height="281" alt="PixPin_2026-06-15_15-18-36" src="https://github.com/user-attachments/assets/655520a2-a6b8-4233-aa75-18d1f71dc049" />

## Features

- 打开 `.txt` 文件，自动尝试 `utf-8`、`gb18030`、`gbk`、`big5` 等常见编码。
- 记住上次打开的文件、窗口大小位置和阅读进度。
- 显示当前阅读百分比，可输入 `50.01` 或 `50.01%` 跳转到指定进度。
- 背景透明度和文字透明度分离。
- 字体、字号、文字颜色、背景颜色可调。
- 拖动小说文字区域即可移动窗口。
- 拖动窗口任意边缘或四角都可以缩放，透明后也可操作。
- 自适应紧凑工具栏：窗口变窄时，字号、透明度、设置等操作会折叠到“更多”菜单。
- 可隐藏工具栏；隐藏后右上角保留一个小入口，右键也可呼出菜单。
- 支持自定义快捷键，Windows 下支持全局最小化热键。

默认快捷键：

- `Ctrl+O`: 打开 TXT
- `Ctrl+H`: 显示/隐藏工具栏
- `Ctrl+,`: 打开设置
- `Ctrl+Alt+M`: 一键最小化

## Quick Start

### 方式一：运行源码

```powershell
python -m pip install -r requirements.txt
python app.py
```

也可以双击：

```text
run.bat
```

### 方式二：下载 exe

普通用户建议在 GitHub Releases 页面下载 `FishReader.exe`，无需安装 Python。

## Build exe

```powershell
.\scripts\build_exe.ps1
```

或：

```bat
scripts\build_exe.bat
```

生成文件：

```text
dist\FishReader.exe
```

## Project Structure

```text
.
├─ app.py
├─ run.bat
├─ requirements.txt
├─ requirements-dev.txt
├─ scripts/
│  ├─ build_exe.bat
│  └─ build_exe.ps1
├─ .github/workflows/
│  └─ build-windows.yml
├─ RELEASE.md
├─ LICENSE
└─ README.md
```

## Settings

运行时设置会保存在当前目录的 `settings.json`。它不会提交到仓库。删除该文件即可恢复默认设置。

## Publish to GitHub

初始化仓库并推送：

```powershell
git init
git add .
git commit -m "Initial release"
git branch -M main
git remote add origin https://github.com/<your-name>/<your-repo>.git
git push -u origin main
```

发布 exe：

1. 在本地运行 `.\scripts\build_exe.ps1`。
2. 确认 `dist\FishReader.exe` 能正常打开。
3. 在 GitHub 仓库页面进入 **Releases**。
4. 创建 `v0.1.0`。
5. 上传 `dist\FishReader.exe`。

也可以推送 `v*` 标签后，用 GitHub Actions 自动构建 exe：

```powershell
git tag v0.1.0
git push origin v0.1.0
```

## License

MIT License. See [LICENSE](LICENSE).
