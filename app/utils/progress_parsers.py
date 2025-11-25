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
    """
    Parser for wget download progress output.
    
    Wget outputs progress in formats like:
    - filename           50%[====>        ] 50.0M  45.3MB/s  eta 5s
    - 'filename' saved [104857600/104857600]
    - Resolving host... IP
    - Connecting to host|IP|:443... connected.
    """
    
    # Progress bar pattern: filename  percent[bar] size speed eta
    PROGRESS_PATTERN = re.compile(
        r'(\S+)\s+(\d+)%\[[=\s>\.]*\]\s*([\d.]+[KMGT]?)\s+([\d.]+[KMGT]?B/s)\s+eta\s+(\d+s?)'
    )
    
    # File saved pattern: 'filename' saved [size/size]
    SAVED_PATTERN = re.compile(r"'([^']+)'\s+saved\s+\[(\d+)/(\d+)\]")
    
    # HTTP response pattern
    HTTP_RESPONSE = re.compile(r'HTTP request sent, awaiting response\.\.\.\s+(\d+)\s+(.+)')
    
    # Connection pattern
    CONNECTING = re.compile(r'Connecting to\s+(.+)\.\.\.\s+connected')
    
    @classmethod
    def parse_line(cls, line: str) -> Optional[Dict]:
        """Parse a line of wget output"""
        
        # Check for progress bar
        match = cls.PROGRESS_PATTERN.search(line)
        if match:
            return {
                'type': 'progress',
                'stage': 'download',
                'filename': match.group(1),
                'percent': int(match.group(2)),
                'downloaded': match.group(3),
                'speed': match.group(4),
                'eta': match.group(5)
            }
        
        # Check for file saved (completion)
        match = cls.SAVED_PATTERN.search(line)
        if match:
            return {
                'type': 'stage_complete',
                'filename': match.group(1),
                'size': int(match.group(2)),
                'percent': 100
            }
        
        # Check for HTTP response
        match = cls.HTTP_RESPONSE.search(line)
        if match:
            return {
                'type': 'http_response',
                'status_code': int(match.group(1)),
                'status_text': match.group(2)
            }
        
        # Check for connection established
        match = cls.CONNECTING.search(line)
        if match:
            return {
                'type': 'connecting',
                'host': match.group(1)
            }
        
        return None
