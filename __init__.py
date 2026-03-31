"""
ERLE Analyzer - Echo Return Loss Enhancement Offline Analyzer

ERLE 离线分析工具包，用于 AEC（声学回声消除）性能评估。

模块：
- erle_analyzer: 单文件 ERLE 分析
- erle_batch_analyze: 批量 ERLE 分析

作者：Wang He
日期：2026-03-12
版本：v1.0
"""

__version__ = "1.0"
__author__ = "Wang He"

from .erle_analyzer import (
    analyze_files,
    analyze_erle,
    read_audio_file,
    read_wav_file,
    read_pcm_file,
    get_erle_rating,
    dbfs_to_linear,
    linear_to_dbfs,
    DEFAULT_SAMPLE_RATE,
    REF_THRESHOLD_DBFS,
    REC_THRESHOLD_DBFS,
    DOUBLE_TALK_ERLE_THRESHOLD,
)

__all__ = [
    'analyze_files',
    'analyze_erle',
    'read_audio_file',
    'read_wav_file',
    'read_pcm_file',
    'get_erle_rating',
    'dbfs_to_linear',
    'linear_to_dbfs',
    'DEFAULT_SAMPLE_RATE',
    'REF_THRESHOLD_DBFS',
    'REC_THRESHOLD_DBFS',
    'DOUBLE_TALK_ERLE_THRESHOLD',
    '__version__',
    '__author__',
]
