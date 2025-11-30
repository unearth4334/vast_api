#!/usr/bin/env python3
"""
Standalone SSH Connectivity Test Utility

A simple command-line tool to test SSH connectivity to configured hosts.
Can be run independently or integrated into CI/CD pipelines.
"""

import argparse
import sys
import os
import subprocess
import logging
import json
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SSHTester:
    """SSH connectivity tester"""
    
    def __init__(self, ssh_config_path: str = None):
        """
        Initialize SSH tester
        
        Args:
            ssh_config_path: Path to SSH config file
        """
        self.ssh_config_path = ssh_config_path or self._find_ssh_config()
        self.default_targets = ['forge', 'comfy']
    
    def _find_ssh_config(self) -> str:
        """Find SSH config file"""
        # Try container path first
        container_path = '/root/.ssh/config'
        if os.path.exists(container_path):
            return container_path
        
        # Try relative path
        relative_path = os.path.join(os.path.dirname(__file__), '.ssh', 'config')
        if os.path.exists(relative_path):
            return relative_path
        
        # Try current directory
        current_path = '.ssh/config'
        if os.path.exists(current_path):
            return current_path
        
        raise FileNotFoundError("SSH config file not found")
    
    def test_host(self, host_alias: str, timeout: int = 10) -> Dict:
        """
        Test SSH connection to a specific host
        
        Args:
            host_alias: SSH host alias from config
            timeout: Connection timeout in seconds
            
        Returns:
            dict: Test result
        """
        try:
            logger.info(f"Testing SSH connection to {host_alias}...")
            
            # Use proper StrictHostKeyChecking to detect host verification issues
            cmd = [
                'ssh',
                '-F', self.ssh_config_path,
                '-o', f'ConnectTimeout={timeout}',
                '-o', 'BatchMode=yes',
                '-o', 'StrictHostKeyChecking=yes',
                '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
                host_alias,
                'echo "ssh-test-success"'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 5  # Add buffer to subprocess timeout
            )
            
            if result.returncode == 0 and 'ssh-test-success' in result.stdout:
                return {
                    'host': host_alias,
                    'success': True,
                    'message': 'Connection successful',
                    'response_time': 'Unknown',  # Could add timing if needed
                    'output': result.stdout.strip()
                }
            else:
                # Check for host key verification issues
                stderr = result.stderr.lower()
                if 'host key verification failed' in stderr or 'no hostkey alg' in stderr or (result.returncode == 255 and 'connection refused' not in stderr):
                    logger.warning(f"Host key verification needed for {host_alias}")
                    return {
                        'host': host_alias,
                        'success': False,
                        'message': 'Host key verification required',
                        'error': result.stderr.strip(),
                        'return_code': result.returncode,
                        'output': result.stdout.strip(),
                        'host_verification_needed': True
                    }
                
                return {
                    'host': host_alias,
                    'success': False,
                    'message': 'Connection failed',
                    'error': result.stderr.strip() or 'No error details',
                    'return_code': result.returncode,
                    'output': result.stdout.strip()
                }
                
        except subprocess.TimeoutExpired:
            return {
                'host': host_alias,
                'success': False,
                'message': f'Connection timed out after {timeout} seconds',
                'error': 'Timeout'
            }
        except Exception as e:
            return {
                'host': host_alias,
                'success': False,
                'message': 'Test failed',
                'error': str(e)
            }
    
    def test_all_hosts(self, targets: List[str] = None, timeout: int = 10) -> Dict:
        """
        Test SSH connection to all specified hosts
        
        Args:
            targets: List of host aliases to test
            timeout: Connection timeout in seconds
            
        Returns:
            dict: Summary of all test results
        """
        if targets is None:
            targets = self.default_targets
        
        results = {}
        success_count = 0
        
        logger.info(f"Testing SSH connectivity to {len(targets)} hosts...")
        
        for target in targets:
            result = self.test_host(target, timeout)
            results[target] = result
            if result['success']:
                success_count += 1
        
        return {
            'summary': {
                'total_hosts': len(targets),
                'successful': success_count,
                'failed': len(targets) - success_count,
                'success_rate': f"{(success_count / len(targets) * 100):.1f}%"
            },
            'results': results
        }
    
    def check_prerequisites(self) -> Dict:
        """
        Check that prerequisites for SSH testing are met
        
        Returns:
            dict: Prerequisites check results
        """
        checks = {}
        
        # Check SSH config file
        checks['ssh_config'] = {
            'path': self.ssh_config_path,
            'exists': os.path.exists(self.ssh_config_path),
            'readable': os.path.exists(self.ssh_config_path) and os.access(self.ssh_config_path, os.R_OK)
        }
        
        # Check SSH command availability
        try:
            subprocess.run(['ssh', '-V'], capture_output=True, check=True)
            checks['ssh_command'] = {'available': True}
        except (subprocess.CalledProcessError, FileNotFoundError):
            checks['ssh_command'] = {'available': False}
        
        # Check SSH key (optional)
        key_paths = [
            '/root/.ssh/id_ed25519',
            os.path.join(os.path.dirname(self.ssh_config_path), 'id_ed25519')
        ]
        
        checks['ssh_key'] = {'found': False}
        for key_path in key_paths:
            if os.path.exists(key_path):
                checks['ssh_key'] = {
                    'found': True,
                    'path': key_path,
                    'readable': os.access(key_path, os.R_OK)
                }
                break
        
        return checks


def print_results(results: Dict, output_format: str = 'text'):
    """Print test results in specified format"""
    
    if output_format == 'json':
        print(json.dumps(results, indent=2))
        return
    
    # Text format
    print("\n" + "="*60)
    print("🔧 SSH Connectivity Test Results")
    print("="*60)
    
    if 'summary' in results:
        summary = results['summary']
        print(f"\n📊 Summary:")
        print(f"   Total hosts tested: {summary['total_hosts']}")
        print(f"   Successful: {summary['successful']}")
        print(f"   Failed: {summary['failed']}")
        print(f"   Success rate: {summary['success_rate']}")
        
        print(f"\n📋 Individual Results:")
        for host, result in results['results'].items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"   {host:10} {status:8} - {result['message']}")
            
            if not result['success'] and 'error' in result:
                print(f"             Error: {result['error']}")
    else:
        # Single host result
        host = results.get('host', 'unknown')
        status = "✅ PASS" if results['success'] else "❌ FAIL"
        print(f"\n{host}: {status}")
        print(f"Message: {results['message']}")
        
        if not results['success'] and 'error' in results:
            print(f"Error: {results['error']}")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description='Test SSH connectivity to configured hosts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test all default hosts (forge, comfy)
  python ssh_test.py
  
  # Test specific host
  python ssh_test.py --host forge
  
  # Test with custom timeout
  python ssh_test.py --timeout 20
  
  # Output as JSON
  python ssh_test.py --format json
  
  # Check prerequisites only
  python ssh_test.py --check-prereqs
        """
    )
    
    parser.add_argument(
        '--host',
        help='Test specific host alias (e.g., forge, comfy)'
    )
    
    parser.add_argument(
        '--hosts',
        nargs='+',
        help='Test multiple specific hosts'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Connection timeout in seconds (default: 10)'
    )
    
    parser.add_argument(
        '--config',
        help='Path to SSH config file'
    )
    
    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    
    parser.add_argument(
        '--check-prereqs',
        action='store_true',
        help='Check prerequisites only'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        tester = SSHTester(args.config)
        
        if args.check_prereqs:
            prereqs = tester.check_prerequisites()
            print("Prerequisites Check:")
            print("=" * 20)
            for check_name, check_result in prereqs.items():
                print(f"{check_name}: {check_result}")
            return
        
        # Determine which hosts to test
        if args.host:
            result = tester.test_host(args.host, args.timeout)
            print_results(result, args.format)
            sys.exit(0 if result['success'] else 1)
        
        elif args.hosts:
            results = tester.test_all_hosts(args.hosts, args.timeout)
        else:
            results = tester.test_all_hosts(timeout=args.timeout)
        
        print_results(results, args.format)
        
        # Exit with error code if any tests failed
        success_rate = results['summary']['successful'] / results['summary']['total_hosts']
        sys.exit(0 if success_rate == 1.0 else 1)
        
    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(3)


if __name__ == '__main__':
    main()