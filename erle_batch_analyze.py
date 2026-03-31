#!/usr/bin/env python3
"""
ERLE 批量分析工具
Batch ERLE Analyzer for Multiple Files

功能：
- 批量分析目录中的所有测试文件
- 自动匹配文件对（rec/ref/out）
- 生成汇总统计表格
- 支持 CSV 和 Markdown 格式输出

作者：Wang He
日期：2026-03-12
版本：v1.0
"""

import argparse
import os
import sys
import glob
import csv
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# 导入单文件分析器
from erle_analyzer import analyze_files, FileStats, DEFAULT_SAMPLE_RATE


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class BatchResult:
    """批量分析结果"""
    file_id: str
    file_rec: str
    file_ref: str
    file_out: Optional[str]
    duration_sec: float
    total_segments: int
    valid_segments: int
    exclusion_rate: float
    erle_avg: float
    erle_std: float
    erle_min: float
    erle_max: float
    rating: str
    silence_ref_count: int
    silence_rec_count: int
    double_talk_count: int
    error_message: str = ""


# ============================================================================
# 文件匹配
# ============================================================================

def find_file_pairs(
    directory: str,
    pattern_rec: str = "*_mic.wav",
    pattern_ref: str = "*_lpb.wav",
    pattern_out: Optional[str] = None
) -> Dict[str, Dict[str, str]]:
    """
    在目录中查找匹配的测试文件对

    命名约定:
    - 麦克风文件：{base}_mic.wav 或 {base}_rec.wav
    - 参考文件：{base}_lpb.wav 或 {base}_ref.wav
    - 输出文件：{base}_output.wav 或 {base}_out.wav (可选)

    Args:
        directory: 搜索目录
        pattern_rec: 麦克风文件匹配模式
        pattern_ref: 参考文件匹配模式
        pattern_out: 输出文件匹配模式

    Returns:
        字典：{base_name: {'rec': path, 'ref': path, 'out': path}}
    """
    pairs = {}

    # 查找所有麦克风文件
    mic_files = glob.glob(os.path.join(directory, pattern_rec))
    mic_files += glob.glob(os.path.join(directory, "*_rec.wav"))
    mic_files += glob.glob(os.path.join(directory, "*_rec.pcm"))
    mic_files += glob.glob(os.path.join(directory, "*_mic.pcm"))

    for mic_path in mic_files:
        # 提取 base name
        base = os.path.basename(mic_path)
        for suffix in ['_mic.wav', '_rec.wav', '_mic.pcm', '_rec.pcm']:
            if base.endswith(suffix):
                base = base[:-len(suffix)]
                break

        # 查找对应的参考文件
        ref_path = None
        for ref_pattern in [f"{base}_lpb.wav", f"{base}_ref.wav", f"{base}_lpb.pcm", f"{base}_ref.pcm"]:
            if os.path.exists(os.path.join(directory, ref_pattern)):
                ref_path = os.path.join(directory, ref_pattern)
                break

        # 查找对应的输出文件
        out_path = None
        if pattern_out:
            out_path = os.path.join(directory, pattern_out.format(base=base))
        else:
            for out_pattern in [f"{base}_output.wav", f"{base}_out.wav", f"{base}_output.pcm"]:
                if os.path.exists(os.path.join(directory, out_pattern)):
                    out_path = os.path.join(directory, out_pattern)
                    break

        if ref_path:
            pairs[base] = {
                'rec': mic_path,
                'ref': ref_path,
                'out': out_path
            }

    return pairs


# ============================================================================
# 批量分析
# ============================================================================

def batch_analyze(
    directory: str,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    segment_size_ms: int = 100,
    output_csv: Optional[str] = None,
    output_md: Optional[str] = None,
    verbose: bool = True
) -> List[BatchResult]:
    """
    批量分析目录中的所有测试文件

    Args:
        directory: 测试文件目录
        sample_rate: 采样率
        segment_size_ms: 分段大小（毫秒）
        output_csv: CSV 输出路径
        output_md: Markdown 输出路径
        verbose: 是否输出详细信息

    Returns:
        批量分析结果列表
    """
    if verbose:
        print("=" * 80)
        print("                    ERLE 批量分析工具 v1.0")
        print("=" * 80)
        print(f"分析目录：{directory}")
        print(f"采样率：{sample_rate} Hz")
        print(f"分段大小：{segment_size_ms} ms")
        print()

    # 查找文件对
    pairs = find_file_pairs(directory)

    if not pairs:
        print("❌ 未找到匹配的测试文件对")
        print("文件命名约定:")
        print("  - 麦克风：{base}_mic.wav 或 {base}_rec.wav")
        print("  - 参考文件：{base}_lpb.wav 或 {base}_ref.wav")
        print("  - 输出文件：{base}_output.wav (可选)")
        return []

    if verbose:
        print(f"找到 {len(pairs)} 对测试文件")
        print()

    results = []

    for i, (file_id, paths) in enumerate(pairs.items(), 1):
        if verbose:
            print(f"[{i}/{len(pairs)}] 分析：{file_id}")

        try:
            stats = analyze_files(
                rec_file=paths['rec'],
                ref_file=paths['ref'],
                out_file=paths['out'],
                sample_rate=sample_rate,
                segment_size_ms=segment_size_ms,
                verbose=False
            )

            result = BatchResult(
                file_id=file_id,
                file_rec=paths['rec'],
                file_ref=paths['ref'],
                file_out=paths['out'],
                duration_sec=stats.duration_sec,
                total_segments=stats.total_segments,
                valid_segments=stats.valid_segments,
                exclusion_rate=stats.exclusion_rate,
                erle_avg=stats.erle_avg,
                erle_std=stats.erle_std,
                erle_min=stats.erle_min,
                erle_max=stats.erle_max,
                rating=stats.rating,
                silence_ref_count=stats.silence_ref_count,
                silence_rec_count=stats.silence_rec_count,
                double_talk_count=stats.double_talk_count
            )
            results.append(result)

            if verbose:
                print(f"  ERLE: {stats.erle_avg:.2f} dB, 评级：{stats.rating}")

        except Exception as e:
            if verbose:
                print(f"  ❌ 错误：{e}")

            results.append(BatchResult(
                file_id=file_id,
                file_rec=paths['rec'],
                file_ref=paths['ref'],
                file_out=paths['out'],
                duration_sec=0,
                total_segments=0,
                valid_segments=0,
                exclusion_rate=0,
                erle_avg=0,
                erle_std=0,
                erle_min=0,
                erle_max=0,
                rating="错误",
                silence_ref_count=0,
                silence_rec_count=0,
                double_talk_count=0,
                error_message=str(e)
            ))

    # 生成报告
    if output_csv:
        save_csv_report(results, output_csv)
        if verbose:
            print(f"\nCSV 报告已保存：{output_csv}")

    if output_md:
        save_markdown_report(results, output_md, directory)
        if verbose:
            print(f"Markdown 报告已保存：{output_md}")

    # 打印汇总
    if verbose:
        print_summary(results)

    return results


# ============================================================================
# 报告生成
# ============================================================================

def save_csv_report(results: List[BatchResult], output_path: str) -> None:
    """保存 CSV 格式报告"""

    fieldnames = [
        'file_id', 'file_rec', 'file_ref', 'file_out',
        'duration_sec', 'total_segments', 'valid_segments', 'exclusion_rate',
        'erle_avg', 'erle_std', 'erle_min', 'erle_max',
        'rating', 'silence_ref_count', 'silence_rec_count', 'double_talk_count',
        'error_message'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in results:
            writer.writerow({
                'file_id': r.file_id,
                'file_rec': r.file_rec,
                'file_ref': r.file_ref,
                'file_out': r.file_out or '',
                'duration_sec': f"{r.duration_sec:.2f}",
                'total_segments': r.total_segments,
                'valid_segments': r.valid_segments,
                'exclusion_rate': f"{r.exclusion_rate:.4f}",
                'erle_avg': f"{r.erle_avg:.2f}",
                'erle_std': f"{r.erle_std:.2f}",
                'erle_min': f"{r.erle_min:.2f}",
                'erle_max': f"{r.erle_max:.2f}",
                'rating': r.rating,
                'silence_ref_count': r.silence_ref_count,
                'silence_rec_count': r.silence_rec_count,
                'double_talk_count': r.double_talk_count,
                'error_message': r.error_message
            })


def save_markdown_report(
    results: List[BatchResult],
    output_path: str,
    directory: str
) -> None:
    """保存 Markdown 格式报告"""

    lines = []
    lines.append("# ERLE 批量分析报告")
    lines.append("")
    lines.append(f"**分析目录**: `{directory}`")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 汇总统计
    valid_results = [r for r in results if r.error_message == ""]
    if valid_results:
        erle_values = [r.erle_avg for r in valid_results]
        lines.append("## 汇总统计")
        lines.append("")
        lines.append(f"- **测试文件数**: {len(valid_results)}")
        lines.append(f"- **平均 ERLE**: {sum(erle_values)/len(erle_values):.2f} dB")
        lines.append(f"- **最大 ERLE**: {max(erle_values):.2f} dB")
        lines.append(f"- **最小 ERLE**: {min(erle_values):.2f} dB")
        lines.append("")

        # 评级分布
        rating_counts = {}
        for r in valid_results:
            rating_counts[r.rating] = rating_counts.get(r.rating, 0) + 1

        lines.append("### 评级分布")
        lines.append("")
        for rating, count in sorted(rating_counts.items()):
            lines.append(f"- {rating}: {count} 个文件")
        lines.append("")

    # 详细结果
    lines.append("## 详细结果")
    lines.append("")
    lines.append("| 文件 ID | 时长 (秒) | 有效段/总段数 | 排除率 | ERLE (dB) | 评级 |")
    lines.append("|---------|-----------|--------------|--------|-----------|------|")

    for r in results:
        if r.error_message:
            lines.append(f"| {r.file_id} | - | - | - | ❌ {r.error_message} | 错误 |")
        else:
            seg_ratio = f"{r.valid_segments}/{r.total_segments}"
            exc_rate = f"{r.exclusion_rate*100:.1f}%"
            lines.append(f"| {r.file_id} | {r.duration_sec:.1f} | {seg_ratio} | {exc_rate} | {r.erle_avg:.2f} | {r.rating} |")

    lines.append("")

    # 错误信息
    error_results = [r for r in results if r.error_message]
    if error_results:
        lines.append("## 错误信息")
        lines.append("")
        for r in error_results:
            lines.append(f"- **{r.file_id}**: {r.error_message}")
        lines.append("")

    # 排除原因统计
    if valid_results:
        total_silence_ref = sum(r.silence_ref_count for r in valid_results)
        total_silence_rec = sum(r.silence_rec_count for r in valid_results)
        total_double_talk = sum(r.double_talk_count for r in valid_results)

        lines.append("## 排除原因统计")
        lines.append("")
        lines.append(f"- 参考信号静默：**{total_silence_ref}** 段")
        lines.append(f"- 麦克风静默：**{total_silence_rec}** 段")
        lines.append(f"- 双讲检测：**{total_double_talk}** 段")
        lines.append("")

    lines.append("---")
    lines.append("*由 ERLE 批量分析工具 v1.0 生成*")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


def print_summary(results: List[BatchResult]) -> None:
    """打印汇总信息"""

    print()
    print("=" * 80)
    print("                           汇总统计")
    print("=" * 80)

    valid_results = [r for r in results if r.error_message == ""]

    if not valid_results:
        print("❌ 没有成功的测试结果")
        return

    erle_values = [r.erle_avg for r in valid_results]

    print(f"测试文件数：{len(valid_results)}")
    print(f"平均 ERLE : {sum(erle_values)/len(erle_values):.2f} dB")
    print(f"最大 ERLE : {max(erle_values):.2f} dB")
    print(f"最小 ERLE : {min(erle_values):.2f} dB")
    print()

    # 评级分布
    rating_counts = {}
    for r in valid_results:
        rating_counts[r.rating] = rating_counts.get(r.rating, 0) + 1

    print("评级分布:")
    for rating, count in sorted(rating_counts.items()):
        print(f"  {rating}: {count} 个文件")

    # 错误统计
    error_count = len(results) - len(valid_results)
    if error_count > 0:
        print(f"\n错误：{error_count} 个文件处理失败")


# ============================================================================
# CLI 入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ERLE 批量分析工具 - Batch ERLE Analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析目录中的所有测试文件
  python erle_batch_analyze.py /path/to/test_audio

  # 指定输出格式
  python erle_batch_analyze.py /path/to/test_audio --csv results.csv --md results.md

  # PCM 文件指定采样率
  python erle_batch_analyze.py /path/to/pcm --sample-rate 8000
        """
    )

    parser.add_argument('directory',
                        help='测试文件目录')
    parser.add_argument('--sample-rate', type=int, default=DEFAULT_SAMPLE_RATE,
                        help=f'采样率（默认：{DEFAULT_SAMPLE_RATE}）')
    parser.add_argument('--segment-size', type=int, default=100,
                        help='分段大小（毫秒，默认：100ms）')
    parser.add_argument('--csv', default=None,
                        help='输出 CSV 报告路径')
    parser.add_argument('--md', '--markdown', default=None,
                        help='输出 Markdown 报告路径')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='静默模式（仅输出汇总）')

    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"错误：目录不存在：{args.directory}", file=sys.stderr)
        sys.exit(1)

    batch_analyze(
        directory=args.directory,
        sample_rate=args.sample_rate,
        segment_size_ms=args.segment_size,
        output_csv=args.csv,
        output_md=args.md,
        verbose=not args.quiet
    )


if __name__ == '__main__':
    main()
