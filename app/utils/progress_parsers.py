"""
Progress parsers for civitdl, wget, and other download tools.
"""
import re
from typing import Optional, Dict

class CivitdlProgressParser:
    PROGRESS_PATTERN = re.compile(r'(Images|Model|Cache):\s*(\d+)%\|[█▓▒░\s]*\|\s*([\d.]+[KMGT]?i?B?)/([\d.]+[KMGT]?i?B?)\s*\[([^\]]+)\<([^\]]+),\s*([\d.]+[KMGT]?i?B?/s)\]')
    STAGE_START = re.compile(r'Now downloading "([^"]+)"')
    STAGE_COMPLETE = re.compile(r'Download completed for "([^"]+)"')

    @classmethod
    def parse_line(cls, line: str) -> Optional[Dict]:
        match = cls.STAGE_START.search(line)
        if match:
            return {'type': 'stage_start', 'name': match.group(1)}
        match = cls.STAGE_COMPLETE.search(line)
        if match:
            return {'type': 'stage_complete', 'name': match.group(1)}
        match = cls.PROGRESS_PATTERN.search(line)
        if match:
            return {
                'type': 'progress',
                'stage': match.group(1).lower(),
                'percent': int(match.group(2)),
                'downloaded': match.group(3),
                'total': match.group(4),
                'elapsed': match.group(5),
                'remaining': match.group(6),
                'speed': match.group(7)
            }
        return None

class WgetProgressParser:
    # TODO: Implement wget progress parsing
    @staticmethod
    def parse_line(line: str) -> Optional[Dict]:
        # Placeholder: parse wget output for progress
        return None
