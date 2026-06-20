# 剪映加密视频解密工具

解密剪映 (JianyingPro / CapCut) 导出的被 XOR 0x2b 加密的视频文件，恢复为标准可播放 MP4。

## 背景

剪映在渲染导出时，`combination` 目录下会生成被 XOR 0x2b 逐字节加密的 MP4 文件，普通播放器无法读取。本工具对其解密，恢复出完整的标准 MP4。

### 加密原理

```
剪映加密文件结构:
  [加密区域]  ftyp + wide + mdat + moov   ← XOR 0x2b 逐字节加密
  [未加密]    bdve + crpt + size          ← 剪映自定义 box (加密元数据)
```

解密只需对加密区域做同样的 XOR 0x2b 即可还原。尾部 `bdve`/`crpt`/`size` 是剪映的自定义 box，不需要解密，直接丢弃即可。

## 使用方法

### 依赖

- Python 3
- ffmpeg (仅封装步骤需要，用于添加 faststart)

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### 运行

```bash
# 默认解密当前目录下的 video1.mp4
python3 merge_jianying_videos.py

# 指定文件名
python3 merge_jianying_videos.py my_video.mp4
```

输出文件 `完整视频.mp4` 会生成在当前目录。

### 输出说明

- 编码格式**跟随原视频** (H.264 / H.265)，使用 `ffmpeg -c copy` 直接复制流，不重新编码
- 无损、快速
- 添加 `+faststart` 标志，支持 Web 渐进式播放

## 文件说明

| 文件 | 说明 |
|------|------|
| `merge_jianying_videos.py` | 解密脚本 |
| `video1.mp4` | 输入：剪映加密的主视频 (需要自行放置) |
| `完整视频.mp4` | 输出：解密后的标准 MP4 |

## 工作流程

```
1. 读取加密文件，定位加密区域边界 (搜索尾部 bdve box)
2. 对加密区域逐字节 XOR 0x2b 解密
3. 验证解密后的 MP4 box 结构 (ftyp / mdat / moov)
4. ffmpeg -c copy 封装为标准 MP4 (+faststart)
5. 清理临时文件
```

## 限制

- 仅适用于 XOR 0x2b 加密方案 (剪映当前版本)
- 不处理 Alpha 通道合并 (如需带透明度的视频，可自行用 ffmpeg alphamerge 滤镜处理)

## License

MIT
