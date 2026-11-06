# 图纸重绘 Skill

把机械图纸（扫描件、照片、PDF、DWG、DXF）重绘成和原图一致的可编辑 CAD 图。**看不清的地方先提问，不猜测；交付前按原图逐线检查。**

## 怎么用

| 工具 | 用法 |
|---|---|
| Claude Code | 把整个文件夹放到 `~/.claude/skills/drawing-redraw/`，然后发图纸并说“用 drawing-redraw 重绘” |
| 其他 AI（ChatGPT、Grok 等） | 把 [PROMPT.md](PROMPT.md) 的全文和图纸一起发过去 |
| 能读取网页的 AI | 也可以发 PROMPT.md 的 Raw 链接，让它先读取（仅公开仓库可用） |

只有 Claude Code 能按 Skill 的方式自动加载。其他工具都是把这份流程当作提示词来用。

## 不同工具能做到的程度

每个工具的能力不同，下面是通用规律，具体要看你用的产品：

| 工具的能力 | 能做到什么 |
|---|---|
| 能读图，能运行代码，能生成文件 | 可以走完整流程，并用 `scripts/` 做量化检查 |
| 能读图，不能运行代码 | 只能读图、提问和列清单，生成不了真正的 CAD 文件，也做不了像素差异检查 |
| 不能读图 | 无法使用 |

DWG 需要另外安装 ODA File Converter。没有它时，可以交付 PDF 和 DXF。

## 工作流程

1. **读图和提问：** 抄录全部内容，把看不清的地方截图发给你，然后等你回答。
2. **工程师画图：** 按原图逐条描线。
3. **检查员检查：** 用差异图和并排对照逐线检查，有差异就退回修改。
4. **交付：** 发文件和对照图，说明查了什么、没查什么、哪里和原图不同。

你要做的只有三件事：发图、回答问题、请工程师校对。**这个流程能减少错误，但不能保证零错误，图纸用于加工前仍需人工校对。**

## 文件

| 文件 | 内容 |
|---|---|
| `SKILL.md` | Claude Code 使用的 Skill |
| `PROMPT.md` | 给其他 AI 使用的提示词 |
| `references/inspection-checklist.md` | 检查员清单 |
| `references/standards.md` | 制图标准清单 |
| `scripts/` | 校准、画图、对照、差异、圆弧测量和压线检查脚本 |

## 脚本

```bash
pip install -r requirements.txt
cd scripts
python calibrate.py config.json work
python side_by_side.py work/calibration.json redraw.pdf work/z Left,-430,-225,-195,195,4
python pixel_diff.py work/calibration.json redraw.pdf work/z Left,-430,-225,-195,195,4
python radial_rings.py work/calibration.json -240 -1 20 185 238 262
python clash_check.py redraw.dxf
```

`config.json` 的格式见 `calibrate.py` 开头的说明。不要把客户图纸提交到公开仓库，`.gitignore` 默认已排除常见的图纸和图片格式。
