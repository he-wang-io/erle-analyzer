#!/usr/bin/env python3
"""
ERLE 离线分析工具 (独立版本)
Echo Return Loss Enhancement Offline Analyzer

功能：
- 支持 PCM 和 WAV 格式输入
- 分段计算 + 能量门限（符合 ITU-T G.168 和 WebRTC 标准）
- 排除静默段和双讲段
- 生成完整的统计分析报告

作者：Wang He
日期：2026-03-12
版本：v1.0
"""

import argparse
import wave
import struct
import math
import json
import os
import sys
from datetime import datetime
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, asdict

# ============================================================================
# 常量定义
# ============================================================================

FULL_SCALE = 32767  # 16-bit 最大值
DEFAULT_SAMPLE_RATE = 16000

# 能量阈值（与 WebRTC 一致，符合 ITU-T G.168 标准）
REF_THRESHOLD_DBFS = -46  # 参考信号能量阈值
REC_THRESHOLD_DBFS = -46  # 麦克风信号能量阈值
DOUBLE_TALK_ERLE_THRESHOLD = -3  # 双讲检测阈值
MIN_ERLE = -10  # 最小 ERLE 值（限制）
MAX_ERLE = 60   # 最大 ERLE 值（限制）

# 分析参数
DEFAULT_SEGMENT_SIZE_MS = 100  # 分段大小（毫秒）


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class SegmentStats:
    """单段统计信息"""
    segment_id: int
    time_start_ms: float
    time_end_ms: float
    ref_power_dbfs: float
    rec_power_dbfs: float
    out_power_dbfs: float
    erle: float
    is_valid: bool
    exclude_reason: str = ""  # "silence_ref", "silence_rec", "double_talk", "none"


@dataclass
class FileStats:
    """文件级统计信息"""
    file_rec: str
    file_ref: Optional[str]
    file_out: Optional[str]
    sample_rate: int
    duration_sec: float
    total_segments: int
    valid_segments: int
    excluded_segments: int
    exclusion_rate: float

    # 排除原因统计
    silence_ref_count: int
    silence_rec_count: int
    double_talk_count: int

    # ERLE 统计
    erle_avg: float
    erle_std: float
    erle_min: float
    erle_max: float
    erle_median: float
    erle_p95: float
    erle_p99: float

    # 评估
    rating: str
    rating_description: str


@dataclass
class AnalysisReport:
    """完整分析报告"""
    analysis_time: str
    tool_version: str
    parameters: Dict
    file_stats: FileStats
    segment_stats: List[SegmentStats]
    histogram: Dict


# ============================================================================
# 工具函数
# ============================================================================

def dbfs_to_linear(dbfs: float) -> float:
    """dBFS 转换为线性功率比"""
    return (FULL_SCALE ** 2) * (10 ** (dbfs / 10))


def linear_to_dbfs(linear: float) -> float:
    """线性功率比转换为 dBFS"""
    if linear <= 0:
        return -100.0
    return 10 * math.log10(linear / (FULL_SCALE ** 2) + 1e-10)


def calculate_power(samples: List[int]) -> float:
    """计算信号功率（线性）"""
    if not samples:
        return 0.0
    return sum(s * s for s in samples) / len(samples)


def read_wav_file(filepath: str) -> Tuple[List[int], int]:
    """
    读取 WAV 文件

    Returns:
        samples: 样本列表
        sample_rate: 采样率
    """
    with wave.open(filepath, 'rb') as wf:
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        n_frames = wf.getnframes()
        raw_data = wf.readframes(n_frames)

    # 解析样本
    samples = []
    if sample_width == 1:
        # 8-bit
        for byte in raw_data:
            samples.append((byte - 128) * 256)  # 转换为有符号 16-bit 范围
    elif sample_width == 2:
        # 16-bit
        for i in range(0, len(raw_data), 2):
            samples.append(struct.unpack('<h', raw_data[i:i+2])[0])
    else:
        raise ValueError(f"不支持的采样位宽：{sample_width}")

    # 多声道转单声道（取左声道或平均值）
    if n_channels > 1:
        mono_samples = []
        for i in range(0, len(samples), n_channels):
            # 取第一个声道
            mono_samples.append(samples[i])
        samples = mono_samples

    return samples, sample_rate


def read_pcm_file(filepath: str, sample_rate: int = 16000) -> Tuple[List[int], int]:
    """
    读取 PCM 文件（假设为 16-bit 有符号整数，单声道）

    Returns:
        samples: 样本列表
        sample_rate: 采样率
    """
    with open(filepath, 'rb') as f:
        raw_data = f.read()

    samples = []
    for i in range(0, len(raw_data), 2):
        samples.append(struct.unpack('<h', raw_data[i:i+2])[0])

    return samples, sample_rate


def read_audio_file(filepath: str, sample_rate: int = 16000) -> Tuple[List[int], int]:
    """
    自动识别并读取音频文件（WAV 或 PCM）

    Returns:
        samples: 样本列表
        sample_rate: 采样率
    """
    if filepath.lower().endswith('.wav'):
        return read_wav_file(filepath)
    elif filepath.lower().endswith('.pcm'):
        return read_pcm_file(filepath, sample_rate)
    else:
        # 尝试 WAV，失败则尝试 PCM
        try:
            return read_wav_file(filepath)
        except:
            return read_pcm_file(filepath, sample_rate)


def calculate_statistics(values: List[float]) -> Dict:
    """计算统计指标"""
    if not values:
        return {
            'avg': 0, 'std': 0, 'min': 0, 'max': 0,
            'median': 0, 'p95': 0, 'p99': 0
        }

    n = len(values)
    avg = sum(values) / n

    # 标准差
    variance = sum((x - avg) ** 2 for x in values) / (n - 1) if n > 1 else 0
    std = math.sqrt(variance)

    # 排序
    sorted_vals = sorted(values)
    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]
    median = sorted_vals[n // 2] if n % 2 == 1 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2

    # 百分位数
    p95_idx = int(n * 0.95)
    p99_idx = int(n * 0.99)
    p95 = sorted_vals[min(p95_idx, n - 1)]
    p99 = sorted_vals[min(p99_idx, n - 1)]

    return {
        'avg': avg,
        'std': std,
        'min': min_val,
        'max': max_val,
        'median': median,
        'p95': p95,
        'p99': p99
    }


def get_erle_rating(erle_avg: float) -> Tuple[str, str]:
    """获取 ERLE 评级"""
    if erle_avg >= 25:
        return "优秀", "AEC 性能良好，回声消除彻底"
    elif erle_avg >= 15:
        return "良好", "AEC 正常工作，有少量残余回声"
    elif erle_avg >= 10:
        return "一般", "AEC 效果一般，可能存在可闻回声"
    else:
        return "较差", "AEC 效果较差，需要检查配置或环境"


def calculate_histogram(values: List[float], bins: int = 10) -> Dict:
    """计算直方图数据"""
    if not values:
        return {'bins': [], 'counts': [], 'bin_edges': []}

    min_val = min(values)
    max_val = max(values)

    # 向下取整到 5 的倍数
    min_edge = math.floor(min_val / 5) * 5
    max_edge = math.ceil(max_val / 5) * 5

    bin_width = (max_edge - min_edge) / bins
    bin_edges = [min_edge + i * bin_width for i in range(bins + 1)]

    counts = [0] * bins
    for v in values:
        for i in range(bins):
            if bin_edges[i] <= v < bin_edges[i + 1]:
                counts[i] += 1
                break
        else:
            counts[-1] += 1

    return {
        'bins': [f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}" for i in range(bins)],
        'counts': counts,
        'bin_edges': bin_edges
    }


# ============================================================================
# 核心分析函数
# ============================================================================

def analyze_erle(
    rec_samples: List[int],
    out_samples: List[int],
    ref_samples: Optional[List[int]] = None,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    segment_size_ms: int = DEFAULT_SEGMENT_SIZE_MS
) -> Tuple[List[SegmentStats], Dict]:
    """
    分析 ERLE（分段计算 + 能量门限）

    Args:
        rec_samples: 麦克风输入信号
        out_samples: AEC 处理后输出信号
        ref_samples: 参考信号（远端，可选，用于静默检测）
        sample_rate: 采样率
        segment_size_ms: 分段大小（毫秒）

    Returns:
        segment_stats: 每段统计信息
        summary: 汇总统计
    """
    segment_size = int(sample_rate * segment_size_ms / 1000)

    min_len = min(len(rec_samples), len(out_samples))
    if ref_samples:
        min_len = min(min_len, len(ref_samples))
    total_segments = min_len // segment_size

    segment_stats = []
    erle_values = []

    exclude_reasons = {
        'silence_ref': 0,
        'silence_rec': 0,
        'double_talk': 0,
        'none': 0
    }

    for seg_id in range(total_segments):
        start_idx = seg_id * segment_size
        end_idx = start_idx + segment_size

        rec_seg = rec_samples[start_idx:end_idx]
        out_seg = out_samples[start_idx:end_idx]
        ref_seg = ref_samples[start_idx:end_idx] if ref_samples else None

        # 计算功率
        rec_power = calculate_power(rec_seg)
        out_power = calculate_power(out_seg)
        ref_power = calculate_power(ref_seg) if ref_seg else None

        rec_power_dbfs = linear_to_dbfs(rec_power)
        out_power_dbfs = linear_to_dbfs(out_power)
        ref_power_dbfs = linear_to_dbfs(ref_power) if ref_power is not None else None

        # 检查 1: 参考信号能量（静默检测，如果有 ref 文件）
        if ref_power is not None and ref_power < dbfs_to_linear(REF_THRESHOLD_DBFS):
            segment_stats.append(SegmentStats(
                segment_id=seg_id,
                time_start_ms=seg_id * segment_size_ms,
                time_end_ms=(seg_id + 1) * segment_size_ms,
                ref_power_dbfs=ref_power_dbfs,
                rec_power_dbfs=rec_power_dbfs,
                out_power_dbfs=out_power_dbfs,
                erle=0,
                is_valid=False,
                exclude_reason="silence_ref"
            ))
            exclude_reasons['silence_ref'] += 1
            continue

        # 检查 2: 麦克风信号能量（静默检测）
        if rec_power < dbfs_to_linear(REC_THRESHOLD_DBFS):
            segment_stats.append(SegmentStats(
                segment_id=seg_id,
                time_start_ms=seg_id * segment_size_ms,
                time_end_ms=(seg_id + 1) * segment_size_ms,
                ref_power_dbfs=ref_power_dbfs,
                rec_power_dbfs=rec_power_dbfs,
                out_power_dbfs=out_power_dbfs,
                erle=0,
                is_valid=False,
                exclude_reason="silence_rec"
            ))
            exclude_reasons['silence_rec'] += 1
            continue

        # 计算 ERLE
        if out_power > 0:
            erle = 10 * math.log10(rec_power / out_power)
        else:
            erle = MAX_ERLE

        # 检查 3: 双讲检测
        if erle < DOUBLE_TALK_ERLE_THRESHOLD:
            segment_stats.append(SegmentStats(
                segment_id=seg_id,
                time_start_ms=seg_id * segment_size_ms,
                time_end_ms=(seg_id + 1) * segment_size_ms,
                ref_power_dbfs=ref_power_dbfs,
                rec_power_dbfs=rec_power_dbfs,
                out_power_dbfs=out_power_dbfs,
                erle=erle,
                is_valid=False,
                exclude_reason="double_talk"
            ))
            exclude_reasons['double_talk'] += 1
            continue

        # 限制 ERLE 范围
        erle = max(MIN_ERLE, min(MAX_ERLE, erle))

        segment_stats.append(SegmentStats(
            segment_id=seg_id,
            time_start_ms=seg_id * segment_size_ms,
            time_end_ms=(seg_id + 1) * segment_size_ms,
            ref_power_dbfs=ref_power_dbfs,
            rec_power_dbfs=rec_power_dbfs,
            out_power_dbfs=out_power_dbfs,
            erle=erle,
            is_valid=True,
            exclude_reason="none"
        ))
        exclude_reasons['none'] += 1
        erle_values.append(erle)

    # 汇总统计
    stats = calculate_statistics(erle_values)

    summary = {
        'total_segments': total_segments,
        'valid_segments': exclude_reasons['none'],
        'excluded_segments': total_segments - exclude_reasons['none'],
        'silence_ref_count': exclude_reasons['silence_ref'],
        'silence_rec_count': exclude_reasons['silence_rec'],
        'double_talk_count': exclude_reasons['double_talk'],
        'erle_values': erle_values,
        'erle_stats': stats
    }

    return segment_stats, summary


# ============================================================================
# 报告生成
# ============================================================================

def generate_text_report(
    file_stats: FileStats,
    segment_stats: List[SegmentStats],
    histogram: Dict,
    output_path: Optional[str] = None
) -> str:
    """生成文本格式报告"""

    lines = []
    lines.append("=" * 80)
    lines.append("                    ERLE 离线分析报告")
    lines.append("=" * 80)
    lines.append(f"分析时间：{file_stats.file_rec}")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 文件信息
    lines.append("-" * 80)
    lines.append("📁 文件信息")
    lines.append("-" * 80)
    lines.append(f"麦克风文件 (Rec): {file_stats.file_rec}")
    lines.append(f"参考文件 (Ref)  : {file_stats.file_ref}")
    if file_stats.file_out:
        lines.append(f"输出文件 (Out)  : {file_stats.file_out}")
    lines.append(f"采样率：{file_stats.sample_rate} Hz")
    lines.append(f"时长：{file_stats.duration_sec:.2f} 秒")
    lines.append("")

    # 分段统计
    lines.append("-" * 80)
    lines.append("📊 分段统计")
    lines.append("-" * 80)
    lines.append(f"总段数：{file_stats.total_segments} 段 ({DEFAULT_SEGMENT_SIZE_MS}ms/段)")
    lines.append(f"有效段：{file_stats.valid_segments} 段 ({file_stats.valid_segments/file_stats.total_segments*100:.1f}%)")
    lines.append(f"排除段：{file_stats.excluded_segments} 段 ({file_stats.exclusion_rate*100:.1f}%)")
    lines.append(f"  - 参考信号静默：{file_stats.silence_ref_count} 段")
    lines.append(f"  - 麦克风静默：{file_stats.silence_rec_count} 段")
    lines.append(f"  - 双讲检测：{file_stats.double_talk_count} 段")
    lines.append("")

    # ERLE 统计
    lines.append("-" * 80)
    lines.append("📈 ERLE 统计")
    lines.append("-" * 80)
    lines.append(f"平均值  : {file_stats.erle_avg:.2f} dB")
    lines.append(f"标准差  : {file_stats.erle_std:.2f} dB")
    lines.append(f"最小值  : {file_stats.erle_min:.2f} dB")
    lines.append(f"最大值  : {file_stats.erle_max:.2f} dB")
    lines.append(f"中位数  : {file_stats.erle_median:.2f} dB")
    lines.append(f"P95     : {file_stats.erle_p95:.2f} dB")
    lines.append(f"P99     : {file_stats.erle_p99:.2f} dB")
    lines.append("")

    # 评估
    lines.append("-" * 80)
    lines.append("🏆 评估结果")
    lines.append("-" * 80)
    lines.append(f"评级：{file_stats.rating}")
    lines.append(f"说明：{file_stats.rating_description}")
    lines.append("")

    # 直方图
    lines.append("-" * 80)
    lines.append("📊 ERLE 分布直方图")
    lines.append("-" * 80)

    if histogram['counts']:
        max_count = max(histogram['counts']) if histogram['counts'] else 1
        for i, (bin_label, count) in enumerate(zip(histogram['bins'], histogram['counts'])):
            bar_len = int(40 * count / max_count) if max_count > 0 else 0
            bar = "█" * bar_len
            pct = count / sum(histogram['counts']) * 100 if histogram['counts'] else 0
            lines.append(f"{bin_label:>10} dB | {bar:<40} {count:>4} ({pct:>5.1f}%)")

    lines.append("")
    lines.append("=" * 80)
    lines.append("                         报告结束")
    lines.append("=" * 80)

    report_text = "\n".join(lines)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)

    return report_text


def generate_json_report(
    report: AnalysisReport,
    output_path: str
) -> None:
    """生成 JSON 格式报告"""

    # 转换为可序列化格式
    data = {
        'analysis_time': report.analysis_time,
        'tool_version': report.tool_version,
        'parameters': report.parameters,
        'file_stats': asdict(report.file_stats),
        'histogram': report.histogram,
        'segment_count': len(report.segment_stats)
    }

    # 移除大数组
    if 'erle_values' in data['file_stats']:
        del data['file_stats']['erle_values']

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================================
# 主分析函数
# ============================================================================

def analyze_files(
    rec_file: str,
    ref_file: Optional[str] = None,
    out_file: Optional[str] = None,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    segment_size_ms: int = DEFAULT_SEGMENT_SIZE_MS,
    output_report: Optional[str] = None,
    output_json: Optional[str] = None,
    verbose: bool = True
) -> FileStats:
    """
    分析文件并生成报告

    Args:
        rec_file: 麦克风输入文件路径（.wav 或 .pcm）
        ref_file: 参考信号文件路径（.wav 或 .pcm，可选）
        out_file: AEC 输出文件路径（可选，.wav 或 .pcm）
        sample_rate: 采样率（仅 PCM 文件需要）
        segment_size_ms: 分段大小（毫秒）
        output_report: 文本报告输出路径
        output_json: JSON 报告输出路径
        verbose: 是否输出详细信息

    Returns:
        FileStats: 文件统计信息
    """
    if verbose:
        print("=" * 60)
        print("         ERLE 离线分析工具 v1.0")
        print("=" * 60)
        print(f"麦克风文件 (Rec): {rec_file}")
        if ref_file:
            print(f"参考文件 (Ref)  : {ref_file}")
        if out_file:
            print(f"输出文件 (Out)  : {out_file}")
        print()

    # 读取文件
    if verbose:
        print("读取音频文件...")

    rec_samples, rec_sr = read_audio_file(rec_file, sample_rate)
    ref_samples, ref_sr = read_audio_file(ref_file, sample_rate) if ref_file else (None, sample_rate)

    if out_file:
        out_samples, out_sr = read_audio_file(out_file, sample_rate)
    else:
        # 如果没有输出文件，使用麦克风信号作为输出（用于调试）
        if verbose:
            print("⚠️  未指定输出文件，将使用麦克风信号作为输出（ERLE 将接近 0dB）")
        out_samples = rec_samples.copy()

    # 采样率检查
    if ref_samples and rec_sr != ref_sr:
        print(f"⚠️  警告：Rec 采样率 ({rec_sr}) 与 Ref 采样率 ({ref_sr}) 不一致")

    actual_sample_rate = rec_sr
    duration_sec = len(rec_samples) / actual_sample_rate

    if verbose:
        print(f"采样率：{actual_sample_rate} Hz")
        print(f"Rec 样本数：{len(rec_samples)} ({duration_sec:.2f} 秒)")
        if ref_samples:
            print(f"Ref 样本数：{len(ref_samples)}")
        print()

    # 对齐长度
    min_len = min(len(rec_samples), len(out_samples))
    if ref_samples:
        min_len = min(min_len, len(ref_samples))
    rec_samples = rec_samples[:min_len]
    if ref_samples:
        ref_samples = ref_samples[:min_len]
    out_samples = out_samples[:min_len]

    # 执行分析
    if verbose:
        print("执行 ERLE 分析...")

    segment_stats, summary = analyze_erle(
        rec_samples, out_samples, ref_samples,
        actual_sample_rate, segment_size_ms
    )

    # 生成统计信息
    erle_values = summary['erle_values']
    stats = summary['erle_stats']
    rating, rating_desc = get_erle_rating(stats['avg'])

    file_stats = FileStats(
        file_rec=rec_file,
        file_ref=ref_file,
        file_out=out_file,
        sample_rate=actual_sample_rate,
        duration_sec=duration_sec,
        total_segments=summary['total_segments'],
        valid_segments=summary['valid_segments'],
        excluded_segments=summary['excluded_segments'],
        exclusion_rate=summary['excluded_segments'] / summary['total_segments'] if summary['total_segments'] > 0 else 0,
        silence_ref_count=summary['silence_ref_count'],
        silence_rec_count=summary['silence_rec_count'],
        double_talk_count=summary['double_talk_count'],
        erle_avg=stats['avg'],
        erle_std=stats['std'],
        erle_min=stats['min'],
        erle_max=stats['max'],
        erle_median=stats['median'],
        erle_p95=stats['p95'],
        erle_p99=stats['p99'],
        rating=rating,
        rating_description=rating_desc
    )

    # 生成直方图
    histogram = calculate_histogram(erle_values)

    # 生成报告
    if output_report:
        if verbose:
            print(f"生成文本报告：{output_report}")
        generate_text_report(file_stats, segment_stats, histogram, output_report)

    if output_json:
        if verbose:
            print(f"生成 JSON 报告：{output_json}")

        report = AnalysisReport(
            analysis_time=datetime.now().isoformat(),
            tool_version="1.0",
            parameters={
                'sample_rate': actual_sample_rate,
                'segment_size_ms': segment_size_ms,
                'ref_threshold_dbfs': REF_THRESHOLD_DBFS,
                'rec_threshold_dbfs': REC_THRESHOLD_DBFS,
                'double_talk_threshold': DOUBLE_TALK_ERLE_THRESHOLD
            },
            file_stats=file_stats,
            segment_stats=segment_stats,
            histogram=histogram
        )
        generate_json_report(report, output_json)

    # 输出摘要
    if verbose:
        print()
        print("-" * 60)
        print("分析完成!")
        print("-" * 60)
        print(f"总段数：{file_stats.total_segments} 段")
        print(f"有效段：{file_stats.valid_segments} 段 ({100 - file_stats.exclusion_rate*100:.1f}%)")
        print(f"平均 ERLE: {file_stats.erle_avg:.2f} dB")
        print(f"评级：{file_stats.rating}")
        print()

    return file_stats


# ============================================================================
# CLI 入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ERLE 离线分析工具 - Echo Return Loss Enhancement Analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法（需要输出文件）
  python erle_analyzer.py -r rec.wav -f ref.wav -o out.wav

  # 指定输出报告
  python erle_analyzer.py -r rec.pcm -f ref.pcm -o out.pcm --report result.txt

  # PCM 文件指定采样率
  python erle_analyzer.py -r rec.pcm -f ref.pcm -o out.pcm --sample-rate 16000

  # 静默模式（仅输出结果）
  python erle_analyzer.py -r rec.wav -f ref.wav -o out.wav --quiet
        """
    )

    parser.add_argument('-r', '--rec', required=True,
                        help='麦克风输入文件（.wav 或 .pcm）')
    parser.add_argument('-f', '--ref', default=None,
                        help='参考信号文件（.wav 或 .pcm，可选，用于静默检测）')
    parser.add_argument('-o', '--out', default=None,
                        help='AEC 输出文件（.wav 或 .pcm，可选）')
    parser.add_argument('--sample-rate', type=int, default=DEFAULT_SAMPLE_RATE,
                        help=f'采样率（仅 PCM 文件需要，默认：{DEFAULT_SAMPLE_RATE}）')
    parser.add_argument('--segment-size', type=int, default=DEFAULT_SEGMENT_SIZE_MS,
                        help=f'分段大小（毫秒，默认：{DEFAULT_SEGMENT_SIZE_MS}ms）')
    parser.add_argument('--report', '-R', default=None,
                        help='输出文本报告路径')
    parser.add_argument('--json', '-J', default=None,
                        help='输出 JSON 报告路径')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='静默模式（仅输出 ERLE 值）')

    args = parser.parse_args()

    # 检查文件是否存在
    if not os.path.exists(args.rec):
        print(f"错误：Rec 文件不存在：{args.rec}", file=sys.stderr)
        sys.exit(1)

    if args.ref and not os.path.exists(args.ref):
        print(f"错误：Ref 文件不存在：{args.ref}", file=sys.stderr)
        sys.exit(1)

    if args.out and not os.path.exists(args.out):
        print(f"警告：输出文件不存在：{args.out}", file=sys.stderr)

    verbose = not args.quiet

    try:
        stats = analyze_files(
            rec_file=args.rec,
            ref_file=args.ref,
            out_file=args.out,
            sample_rate=args.sample_rate,
            segment_size_ms=args.segment_size,
            output_report=args.report,
            output_json=args.json,
            verbose=verbose
        )

        # 静默模式只输出 ERLE 值
        if args.quiet:
            print(f"{stats.erle_avg:.2f}")

    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
