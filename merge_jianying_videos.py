#!/usr/bin/env python3
"""
剪映(JianyingPro) 加密视频解密工具
===================================

解密剪映 combination 中被 XOR 0x2b 加密的主视频，
恢复为标准 MP4 (跟随原编码 H.264/H.265，无损无重编码)。

用法:
  python3 merge_jianying_videos.py              # 使用默认文件名 video1.mp4
  python3 merge_jianying_videos.py video2.mp4   # 指定主视频文件名
"""

import os
import sys
import subprocess
import shutil

# XOR 加密密钥
XOR_KEY = 0x2B


def find_encrypted_boundary(data):
    """
    定位加密区域与未加密区域的分界点。

    剪映加密文件结构:
      [加密] ftyp + wide + mdat + moov  ← XOR 0x2b
      [未加密] bdve + crpt + size       ← 剪映自定义 box
    """
    bdve_marker = b'bdve'
    search_start = max(0, len(data) - 1024)
    pos = data.find(bdve_marker, search_start)
    if pos == -1:
        crpt_pos = data.find(b'crpt', search_start)
        if crpt_pos != -1:
            pos = crpt_pos - 8
        else:
            return len(data)
    return pos - 4


def decrypt_main_video(input_path, output_path):
    """对加密的主视频执行 XOR 0x2b 解密。"""
    print(f"\n[Step 1] 解密主视频")
    print(f"  输入: {input_path}")

    with open(input_path, 'rb') as f:
        data = f.read()

    file_size = len(data)
    print(f"  文件大小: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")

    boundary = find_encrypted_boundary(data)
    print(f"  加密区域: 0 ~ {boundary:,} (解密)")
    print(f"  尾部自定义box: {boundary:,} ~ {file_size:,} (跳过, {file_size - boundary} bytes)")

    check = bytes([b ^ XOR_KEY for b in data[4:8]])
    if check != b'ftyp':
        print(f"  ✗ 警告: 解密验证失败，前4字节 XOR 后不是 'ftyp' (得到: {check})")
        print(f"  尝试继续解密...")
    else:
        print(f"  ✓ 验证通过: XOR 0x{XOR_KEY:02X} 解密确认，文件头为 ftyp box")

    print(f"  正在解密 {boundary:,} bytes...")
    decrypted = bytes([b ^ XOR_KEY for b in data[:boundary]])

    print(f"  解密后 box 结构:")
    offset = 0
    boxes = []
    while offset < len(decrypted) - 8:
        box_size = int.from_bytes(decrypted[offset:offset + 4], 'big')
        box_type = decrypted[offset + 4:offset + 8]
        try:
            type_str = box_type.decode('ascii')
        except:
            type_str = f"[{box_type.hex()}]"

        if box_size < 8 or box_size > len(decrypted) - offset + 8:
            print(f"    ⚠ 异常 box at offset {offset}: type={type_str}, size={box_size}")
            break

        print(f"    {type_str}: size={box_size:,}, offset={offset:,}")
        boxes.append((type_str, box_size, offset))
        offset += box_size

    has_moov = any(b[0] == 'moov' for b in boxes)
    has_mdat = any(b[0] == 'mdat' for b in boxes)

    if has_moov and has_mdat:
        print(f"  ✓ 包含 moov(元数据) 和 mdat(媒体数据)，结构完整")
    else:
        missing = []
        if not has_moov:
            missing.append('moov')
        if not has_mdat:
            missing.append('mdat')
        print(f"  ✗ 缺少关键 box: {', '.join(missing)}")

    with open(output_path, 'wb') as f:
        f.write(decrypted)

    print(f"  ✓ 解密文件已保存: {output_path}")
    return True


def export_standard_mp4(decrypted_video, output_path):
    """
    用 ffmpeg -c copy 封装为标准 MP4。
    跟随原编码 (H.264/H.265)，无损无重编码。
    """
    print(f"\n[Step 2] 封装为标准 MP4 (跟随原编码，无损)")

    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_streams', '-show_format', decrypted_video],
            capture_output=True, text=True, timeout=30
        )
        import json
        info = json.loads(result.stdout)
        for s in info.get('streams', []):
            if s['codec_type'] == 'video':
                print(f"  视频流: {s.get('codec_name', '?').upper()} "
                      f"{s['width']}x{s['height']} "
                      f"{eval(s.get('r_frame_rate', '0/1')):.0f}fps "
                      f"{float(s.get('duration', 0)):.1f}s")
            elif s['codec_type'] == 'audio':
                print(f"  音频流: {s.get('codec_name', '?').upper()} "
                      f"{s.get('sample_rate', '?')}Hz "
                      f"{s.get('channels', '?')}ch "
                      f"{float(s.get('duration', 0)):.1f}s")
    except Exception:
        pass

    print(f"  输出: {output_path}")

    cmd = [
        'ffmpeg', '-y',
        '-i', decrypted_video,
        '-c', 'copy',
        '-movflags', '+faststart',
        output_path
    ]

    print(f"  正在封装(直接复制流，无损无重编码)...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0 and os.path.exists(output_path):
        size = os.path.getsize(output_path)
        print(f"  ✓ 导出成功: {output_path}")
        print(f"  输出大小: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")
        return True
    else:
        print(f"  ✗ 导出失败")
        if result.stderr:
            for line in result.stderr.strip().split('\n')[-5:]:
                print(f"    {line}")
        return False


def main():
    print("=" * 60)
    print("  剪映加密视频解密工具")
    print("  XOR 0x2b 解密 → 标准 MP4 (跟随原编码)")
    print("=" * 60)

    # 解析参数: 默认 video1.mp4，也可指定文件名
    if len(sys.argv) >= 2:
        main_video = sys.argv[1]
    else:
        main_video = "video1.mp4"

    # 输出到当前目录
    output_dir = os.getcwd()
    decrypted_path = os.path.join(output_dir, "decrypted_main.mp4")
    output_path = os.path.join(output_dir, "完整视频.mp4")

    # 检查输入文件
    if not os.path.exists(main_video):
        print(f"\n✗ 主视频文件不存在: {main_video}")
        print(f"  用法: python3 merge_jianying_videos.py [加密主视频文件名]")
        print(f"  默认文件名: video1.mp4")
        sys.exit(1)

    # 检查 ffmpeg
    if not shutil.which('ffmpeg'):
        print("\n✗ 未找到 ffmpeg，请先安装: brew install ffmpeg")
        sys.exit(1)

    print(f"输入文件: {main_video}")
    print(f"输出目录: {output_dir}")

    # Step 1: 解密
    if not decrypt_main_video(main_video, decrypted_path):
        print("\n✗ 解密失败")
        sys.exit(1)

    # Step 2: 封装
    mp4_success = export_standard_mp4(decrypted_path, output_path)

    # 总结
    print("\n" + "=" * 60)
    print("  完成!")
    print("=" * 60)

    if mp4_success:
        print(f"\n  📹 完整视频: {output_path}")

    # 清理临时文件
    try:
        os.remove(decrypted_path)
        print(f"  已清理临时文件: {decrypted_path}")
    except:
        pass

    if not mp4_success:
        print(f"\n⚠ 封装失败，但解密文件已生成: {decrypted_path}")
        sys.exit(1)


if __name__ == '__main__':
    main()
