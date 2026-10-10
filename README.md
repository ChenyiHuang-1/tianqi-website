# Tianqi Materials 官网（tianqimaterials.com）

纯静态网站，中英文两套页面。`build.py` 读取 `data/*.json` 和 `pages/` 里的内容，生成可直接发布的 `public/` 文件夹。不需要服务器、数据库或购物车。

## 目录

| 位置 | 内容 |
| --- | --- |
| `data/site.json` | 联系方式、表单服务地址、设计费文字、首页首图和精选纹样 |
| `data/categories.json` | 三大类和子分类（导航下拉和产品总览共用） |
| `data/products.json` | 产品，每款一条，一款只有一个详情页 |
| `data/patterns.json` | UV 纹样，每个编号一条 |
| `data/company.json` | 公司数据、证书、设备、研发成果 |
| `data/i18n.json` | 按钮和界面上的中英文短文字 |
| `pages/en/`、`pages/zh/` | 首页、产品总览、图库、定制、关于、联系页的正文 |
| `templates/base.html` | 页头（导航、语言切换、询价按钮）和页脚 |
| `public/assets/` | 样式、脚本、产品和工厂图片 |
| `public/img/patterns/` | 由构建脚本生成的纹样图（缩略图和清晰图），不要手动改 |

英文页面在 `/`，中文页面在 `/zh/`，右上角按钮在同一页面的两种语言之间切换。

## 运行

需要 Python 3.9 以上和 Pillow：`pip install pillow`

```
python build.py --src "E:\uv\标化"          # 生成新增或改过的纹样图，并重建全部页面
python build.py                             # 只改了文字时，重建页面即可
python build.py --src "E:\uv\标化" --force  # 全部纹样图重新生成
```

本地预览：

```
cd public
python -m http.server 8000
```

然后浏览器打开 http://localhost:8000/ 。

也可以直接双击 `public\index.html` 打开，页面和链接同样可用（询价表单除外）。

## 常见修改

**新增纹样**：把照片按编号命名放进原图文件夹（如 `302.jpg`），同一纹样的其他角度命名为 `302-2.jpg`、`302-3.jpg`。在 `data/patterns.json` 末尾加一条：

```json
{"id": "302", "design_status": "design-ready", "stock_status": "unconfirmed", "carriers": ["paper"], "tags_verified": {"finish": "silver", "pattern": "geometric", "effect": "medium"}, "source": "照片 E:/uv/标化/302.jpg"}
```

运行 `python build.py --src "E:\uv\标化"`。纹样数量自动统计，不用改其他地方。替换清晰原图时文件名保持不变，编号和页面对应关系不受影响。

**纹样标签与筛选**：图库按三组标签筛选，写在 `data/patterns.json` 每款的 `tags_verified` 里，例如 `"tags_verified": {"finish": "holographic", "pattern": "fluid", "effect": "bold"}`。
- `finish` 光泽：`silver` 银色、`pearl` 珍珠彩、`holographic` 彩虹镭射
- `pattern` 图案：`geometric` 几何、`fluid` 流体、`texture` 肌理、`lines` 线条光束、`motif` 主题图案（爱心、星星、花朵等）
- `effect` 效果：`subtle` 低调、`medium` 适中、`bold` 强烈

现有 201 款的标签是按照片人工逐款判断的，觉得哪款不对，直接改那一款的值再重新运行 `build.py`。新增纹样也按这三项填写。

**纹样可做膜材**：确认某款能单独供膜后，把 `carriers` 改成 `["paper", "film"]`，详情页才会显示膜材。

**产品**：在 `data/products.json` 里改。`category` 和 `sub` 对应 `categories.json` 的 id；`structure`（材料结构）、`process`（加工方式）、`effect`（视觉效果）分开写，不知道就填 `null`，页面会自动不显示那一行；`specs` 只写已确认的规格；`attrs` 用于分类页筛选；`image` 写 `assets/img` 下的图片名（不带 .webp），或 `pattern:181` 表示用某个纹样图。`status` 为 `pending-review` 时页面显示“待核对”。

**隐藏或公开子分类**：`categories.json` 里子分类的 `public` 改为 `true` 或 `false`。目前“其他覆膜与涂布纸材”“镀铝 PET 膜”因没有资料而隐藏。

**公司数据和证书**：`company.json` 里每一项都有 `confirmed`，只有改成 `true` 才会出现在网站上。证书请核对当前有效期和适用范围后再改。

**联系方式**：都在 `data/site.json` 里：`email`、`phone`、`whatsapp`、`address`。填写后自动出现在联系页和页脚，留空则不显示。邮箱会生成点开即写邮件的链接，WhatsApp 会生成 wa.me 对话链接，电话会生成可直接拨打的链接。`phone` 可以写多个号码，例如 `["+86 13588811688", "+86 15868411688"]`。
目前用的是个人邮箱 hancyih@gmail.com 和 WhatsApp +44 7894407310。以后换成域名邮箱（如 sales@tianqimaterials.com）时，改两处：`email` 改成新邮箱；`form_endpoint` 改成 `https://formsubmit.co/ajax/新邮箱`。然后重新运行 `python build.py`。换完后在正式网站上提交一次测试询价，并在新邮箱里点击 FormSubmit 的激活链接。

**询价表单**：表单需要一个真实的接收服务（例如 Formspree、Web3Forms，或自建的 Cloudflare Worker）。目前已接 FormSubmit（`form_endpoint` 为 `https://formsubmit.co/ajax/邮箱`，免注册，首次提交后需在邮箱里点激活链接）。换其他服务时，把服务给的地址填进 `site.json` 的 `form_endpoint`。没填时提交按钮是灰的，并提示表单尚未接通，不会假装提交成功。若服务支持附件，把 `form_accepts_files` 改为 `true`，并在 `form_file_note` 写清格式和大小限制。上线前请自己提交一次，确认邮箱真的收到。

**成品效果图换实拍图**：成品四个子分类（包装盒、卡牌与小卡、明信片、其他纸制文创）目前用的是效果图，放在 `public/assets/img/render/`：`packaging-boxes.webp`、`cards-mini-cards.webp`、`postcards.webp`、`paper-merchandise.webp`。拍好实拍图后，转成 webp（建议 1200×900，横版 4:3），用同样的文件名覆盖即可，页面不用改。然后在 `data/categories.json` 对应子分类里把 `"image_is_render": true` 改成 `false`，图片下方的“效果图，仅供示意”说明就会去掉。首页“我们的材料用在哪里”三张卡片左上角的“效果图/Render”标签写在 `pages/zh/home.html` 和 `pages/en/home.html` 里，换图后删掉 `<span class="rtag">…</span>` 即可。效果图的制作文件在 `source-img/render/`。

**设计费**：`site.json` 的 `design_fee`，中英文分别填写，是两个市场各自的报价，不按汇率换算。

改完任何内容都要重新运行 `python build.py`，再提交到 GitHub。

## 发布：GitHub + Cloudflare Pages

1. 把整个项目（包括 `public/`）提交到 GitHub 仓库。纹样原图不进仓库，`.gitignore` 已经排除。
2. Cloudflare 控制台 → Workers & Pages → Create → Pages → Connect to Git，选择这个仓库。
3. 构建设置：Framework preset 选 None，Build command 留空，Build output directory 填 `public`。
4. 部署完成后，在 Custom domains 里添加 `tianqimaterials.com` 和 `www.tianqimaterials.com`。
5. 之后每次本地运行 `build.py` 并推送到 GitHub，Cloudflare 会自动更新网站。

网页上的纹样图是从原图生成的压缩版（缩略图 360×480，详情图宽 1000 像素）。原图越清晰，网页图就越清晰；换成清晰原图后用 `--force` 重新生成即可。
