# jianying-video-merge

合并剪映导出的被 XOR 0x2b 加密的视频文件，恢复为标准可播放 MP4，绕过导出VIP限制。

## 背景

剪映在导出预合成片段时，`combination` 目录下会生成被 XOR 0x2b 逐字节加密的 MP4 文件，普通播放器无法读取。本工具对其解密，恢复出完整的标准 MP4。

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
- ffmpeg

### 如何导出预合成片段？
全选剪映内所有素材，右键新建复合片段。在复合片段上右键，选择预合成复合片段，等待片段渲染完成，此时预合成片段文件就位于 /工程文件目录/Resources/combination 文件夹内

### 运行

```bash
python3 merge_jianying_videos.py 体积较大的视频 体积较小的视频
```

输出文件会生成在当前目录。

### 输出说明

- 编码格式**跟随原视频** (H.264 / H.265)，使用 `ffmpeg -c copy` 直接复制流，不重新编码
- 无损、快速
- 添加 `+faststart` 标志，支持 Web 渐进式播放

## License

MIT
