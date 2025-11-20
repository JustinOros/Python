#!/usr/bin/env python3
# Description: Monero (XMR) Mining Script - Optimized for CPU mining with support for solo and pool mining
# Usage: python3 miner-monero.py
# Author: Justin Oros
# Source: https://github.com/JustinOros 

import json
import subprocess
import sys
import os
import time
import signal
import platform
import urllib.request
import tarfile
import zipfile
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

class MoneroMiner:
    def __init__(self, config_file: str = "miner-monero.json"):
        self.config_file = config_file
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config = None
        self.process: Optional[subprocess.Popen] = None
        
    def detect_os(self) -> str:
        """Detect the operating system"""
        system = platform.system()
        if system == 'Darwin':
            return 'macos'
        elif system == 'Linux':
            return 'linux'
        elif system == 'Windows':
            return 'windows'
        else:
            return 'unknown'
    
    def detect_cpu_arch(self) -> str:
        """Detect CPU architecture"""
        machine = platform.machine().lower()
        if machine in ['arm64', 'aarch64']:
            return 'arm64'
        elif machine in ['x86_64', 'amd64', 'x64']:
            return 'x64'
        elif machine in ['i386', 'i686', 'x86']:
            return 'x86'
        else:
            return machine
    
    def get_latest_xmrig_release(self) -> Optional[Tuple[str, list]]:
        """Fetch the latest XMRig version and available files from GitHub"""
        try:
            url = "https://api.github.com/repos/xmrig/xmrig/releases/latest"
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                version = data['tag_name'].lstrip('v')
                
                # Extract list of asset filenames
                assets = [asset['name'] for asset in data.get('assets', [])]
                
                return version, assets
        except Exception as e:
            print(f"Error fetching latest release info: {e}")
            return None
    
    def find_matching_file(self, assets: list, os_type: str, arch: str) -> Optional[str]:
        """Find the matching file for the given OS and architecture"""
        # Build search patterns based on OS and architecture
        if os_type == 'macos':
            if arch == 'arm64':
                patterns = ['macos-arm64.tar.gz', 'macos-aarch64.tar.gz']
            elif arch == 'x64':
                patterns = ['macos-x64.tar.gz', 'macos-x86_64.tar.gz']
            else:
                return None
        elif os_type == 'linux':
            if arch == 'arm64':
                patterns = ['linux-static-arm64.tar.gz', 'linux-arm64.tar.gz', 'linux-aarch64.tar.gz']
            elif arch == 'x64':
                patterns = ['linux-static-x64.tar.gz', 'linux-x64.tar.gz', 'linux-x86_64.tar.gz']
            else:
                return None
        elif os_type == 'windows':
            if arch == 'x64':
                patterns = ['msvc-win64.zip', 'win64.zip', 'windows-x64.zip']
            elif arch == 'x86':
                patterns = ['msvc-win32.zip', 'win32.zip', 'windows-x86.zip']
            else:
                return None
        else:
            return None
        
        # Search for matching file
        for asset in assets:
            for pattern in patterns:
                if pattern in asset.lower():
                    return asset
        
        return None
    
    def check_xmrig_installed(self) -> bool:
        """Check if xmrig is installed"""
        # Check in script directory first
        local_paths = [
            os.path.join(self.script_dir, 'xmrig'),
            os.path.join(self.script_dir, 'xmrig.exe'),
        ]
        
        for path in local_paths:
            if os.path.exists(path) and os.access(path, os.X_OK if os.name != 'nt' else os.F_OK):
                return True
        
        # Check in system PATH (Unix-like systems)
        if os.name != 'nt':
            try:
                result = subprocess.run(['which', 'xmrig'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=5)
                if result.returncode == 0:
                    return True
            except:
                pass
        else:
            # Windows - check with 'where' command
            try:
                result = subprocess.run(['where', 'xmrig.exe'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=5)
                if result.returncode == 0:
                    return True
            except:
                pass
        
        return False
    
    def download_and_install_xmrig(self) -> bool:
        """Download and install XMRig based on OS and architecture"""
        os_type = self.detect_os()
        arch = self.detect_cpu_arch()
        
        print(f"\nDetected OS: {os_type}")
        print(f"Detected Architecture: {arch}")
        
        if os_type not in ['macos', 'linux', 'windows']:
            print(f"\nAutomatic installation is not supported for this OS.")
            print(f"Please install XMRig manually from: https://github.com/xmrig/xmrig/releases")
            return False
        
        # Get latest release info
        print("\nFetching latest XMRig release from GitHub...")
        release_info = self.get_latest_xmrig_release()
        
        if not release_info:
            print("Could not fetch release information from GitHub.")
            print("Please install XMRig manually from: https://github.com/xmrig/xmrig/releases")
            return False
        
        version, assets = release_info
        print(f"Latest version: {version}")
        print(f"Found {len(assets)} release files")
        
        # Find matching file for this OS and architecture
        filename = self.find_matching_file(assets, os_type, arch)
        
        if not filename:
            print(f"\nCould not find a compatible XMRig release for {os_type} {arch}")
            print(f"Available files:")
            for asset in assets:
                if asset.endswith(('.tar.gz', '.zip')):
                    print(f"  - {asset}")
            print("\nPlease download manually from: https://github.com/xmrig/xmrig/releases")
            return False
        
        print(f"Found matching file: {filename}")
        
        download_url = f"https://github.com/xmrig/xmrig/releases/download/v{version}/{filename}"
        
        print(f"\nReady to download: {filename}")
        print(f"URL: {download_url}")
        
        # Prompt user (default to Yes)
        while True:
            response = input("\nDownload and install XMRig? (Y/N) [Y]: ").strip().upper()
            if response == '':
                response = 'Y'
            if response in ['Y', 'N']:
                break
            print("Please enter Y or N (or press ENTER for Yes)")
        
        if response == 'N':
            print("Installation cancelled.")
            return False
        
        # Download with retry logic
        print(f"\nDownloading {filename}...")
        local_filename = os.path.join(self.script_dir, filename)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(download_url)
                req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
                req.add_header('Accept', '*/*')
                
                with urllib.request.urlopen(req, timeout=30) as response:
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded = 0
                    
                    with open(local_filename, 'wb') as f:
                        while True:
                            chunk = response.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                print(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)
                
                print("\nDownload complete!")
                break
                
            except urllib.error.HTTPError as e:
                print(f"\nHTTP Error {e.code}: {e.reason}")
                if attempt < max_retries - 1:
                    print(f"Retrying... (Attempt {attempt + 2}/{max_retries})")
                    time.sleep(2)
                else:
                    print(f"\nFailed to download after {max_retries} attempts.")
                    print(f"Please download manually from: {download_url}")
                    return False
            except Exception as e:
                print(f"\nError downloading file: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying... (Attempt {attempt + 2}/{max_retries})")
                    time.sleep(2)
                else:
                    print(f"\nFailed to download after {max_retries} attempts.")
                    print(f"Please download manually from: {download_url}")
                    return False
        
        # Extract
        print("Extracting archive...")
        try:
            is_zip = filename.endswith('.zip')
            
            if is_zip:
                # Windows ZIP file
                with zipfile.ZipFile(local_filename, 'r') as zip_ref:
                    # Find the xmrig.exe binary in the archive
                    xmrig_found = False
                    for member in zip_ref.namelist():
                        if member.endswith('xmrig.exe') or member == 'xmrig.exe':
                            # Extract to script directory with name 'xmrig.exe'
                            with zip_ref.open(member) as source:
                                target_path = os.path.join(self.script_dir, 'xmrig.exe')
                                with open(target_path, 'wb') as target:
                                    target.write(source.read())
                            xmrig_found = True
                            break
                    
                    if not xmrig_found:
                        print("Could not find xmrig.exe in the archive")
                        return False
                
                xmrig_path = os.path.join(self.script_dir, 'xmrig.exe')
                print(f"XMRig installed successfully at: {xmrig_path}")
            else:
                # Unix TAR.GZ file
                with tarfile.open(local_filename, 'r:gz') as tar:
                    # Find the xmrig binary in the archive
                    for member in tar.getmembers():
                        if member.name.endswith('/xmrig') or member.name == 'xmrig':
                            member.name = 'xmrig'
                            tar.extract(member, self.script_dir)
                            break
                
                xmrig_path = os.path.join(self.script_dir, 'xmrig')
                
                # Make executable (Unix-like systems)
                os.chmod(xmrig_path, 0o755)
                print(f"XMRig installed successfully at: {xmrig_path}")
            
            # Clean up
            os.remove(local_filename)
            print("Cleaned up temporary files.")
            
            return True
            
        except Exception as e:
            print(f"Error extracting archive: {e}")
            return False
    
    def prompt_wallet_address(self) -> str:
        """Prompt user for wallet address"""
        default_wallet = "85NGrygcwq36kjLaNKZevT53H4EeHRQYeje5Y3gq3GYkKsEpwKpGjqd1tGxAVEjDfxEha6SYtyNYPbmPXduYqy47Q6JwbuW"
        
        print("\n" + "="*60)
        print("Monero Wallet Configuration")
        print("="*60)
        print(f"\nDefault wallet address:")
        print(f"{default_wallet}")
        print("\nPress ENTER to use the default wallet, or paste your own:")
        
        wallet = input("Wallet Address: ").strip()
        
        if not wallet:
            wallet = default_wallet
            print("Using default wallet address.")
        else:
            print("Using your wallet address.")
        
        return wallet
    
    def check_windows_admin(self) -> bool:
        """Check if script is running with Administrator privileges on Windows"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    def prompt_msr_mod(self, os_type: str) -> bool:
        """Prompt user to enable MSR MOD for performance optimization"""
        # MSR MOD is only supported on Windows and Linux
        if os_type not in ['windows', 'linux']:
            return False
        
        print("\n" + "="*60)
        print("MSR MOD - Performance Optimization")
        print("="*60)
        print("\nMSR (Model-Specific Register) modification can improve")
        print("mining performance by 10-50% by optimizing CPU behavior.")
        print("\nNOTE: Requires administrator/root privileges")
        print("WARNING: May cause system instability if misconfigured")
        
        if os_type == 'linux':
            print("\nOn Linux, MSR MOD requires:")
            print("  1. Loading the msr kernel module")
            print("  2. Running the miner with sudo/root")
        elif os_type == 'windows':
            print("\nOn Windows, MSR MOD requires:")
            print("  1. Running as Administrator")
            print("  2. XMRig will automatically load WinRing0 driver")
        
        while True:
            response = input("\nEnable MSR MOD? (Y/N) [N]: ").strip().upper()
            if response == '':
                response = 'N'
            if response in ['Y', 'N']:
                break
            print("Please enter Y or N (or press ENTER for No)")
        
        if response == 'Y':
            print("MSR MOD will be enabled.")
            if os_type == 'windows':
                if not self.check_windows_admin():
                    print("\n⚠ WARNING: Not running as Administrator!")
                    print("  Please restart this script by:")
                    print("  1. Right-click on Command Prompt or PowerShell")
                    print("  2. Select 'Run as Administrator'")
                    print("  3. Run the script again")
                else:
                    print("✓ Running with Administrator privileges")
            else:
                print("\nSetting up MSR support on Linux...")
                self.setup_linux_msr()
            return True
        else:
            print("MSR MOD disabled (standard mining mode).")
            return False
    
    def setup_linux_msr(self):
        """Setup MSR kernel module on Linux"""
        try:
            # Check if msr module is loaded
            result = subprocess.run(['lsmod'], capture_output=True, text=True)
            if 'msr' not in result.stdout:
                print("\nLoading MSR kernel module...")
                print("You may be prompted for your sudo password.")
                
                # Try to load msr module
                result = subprocess.run(['sudo', 'modprobe', 'msr'], 
                                      capture_output=True, 
                                      text=True)
                
                if result.returncode == 0:
                    print("✓ MSR module loaded successfully")
                else:
                    print("⚠ Could not load MSR module automatically")
                    print("  Please run manually: sudo modprobe msr")
            else:
                print("✓ MSR module already loaded")
            
            # Check if running with sudo
            if os.geteuid() != 0:
                print("\n⚠ IMPORTANT: You must run the miner with sudo for MSR to work!")
                print("  Example: sudo python3 miner-monero.py")
            else:
                print("✓ Running with root privileges")
                
        except Exception as e:
            print(f"\n⚠ Could not setup MSR automatically: {e}")
            print("  Manual setup required:")
            print("  1. Run: sudo modprobe msr")
            print("  2. Start miner with: sudo python3 miner-monero.py")
    
    def setup_initial_config(self):
        """Setup initial configuration with user input"""
        os_type = self.detect_os()
        arch = self.detect_cpu_arch()
        is_mac = os_type == 'macos'
        is_arm = arch == 'arm64'
        
        # Get wallet address from user
        wallet_address = self.prompt_wallet_address()
        
        # Prompt for MSR MOD
        enable_msr = self.prompt_msr_mod(os_type)
        
        # Determine xmrig path based on OS
        if os_type == 'windows':
            miner_executable = "xmrig.exe"
        else:
            # macOS and Linux
            miner_executable = "./xmrig"
        
        config = {
            "wallet_address": wallet_address,
            "mining_mode": "pool",
            "miner_executable": miner_executable,
            "pool_address": "pool.supportxmr.com:443",
            "pool_password": "x",
            "worker_name": f"m2-miner" if is_arm else "worker1",
            "node_address": "127.0.0.1:18081",
            "threads": 0,
            "cpu_max_usage": 75,
            "huge_pages": True if not is_mac else False,
            "randomx_mode": "auto",
            "tls_enabled": True,
            "nicehash": False,
            "msr_mod": enable_msr,
            "extra_args": [],
            "log_file": "monero-miner.log",
            "api_port": 0,
            "donate_level": 1
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"\nConfiguration saved to: {self.config_file}")
        return config
        
    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        if not os.path.exists(self.config_file):
            print(f"Configuration file '{self.config_file}' not found.")
            print("Setting up initial configuration...")
            return None
            
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            self.validate_config(config)
            return config
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in configuration file: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)
    
    def validate_config(self, config: Dict):
        """Validate required configuration fields"""
        required_fields = ['wallet_address', 'mining_mode']
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        
        if config['mining_mode'] not in ['solo', 'pool']:
            raise ValueError("mining_mode must be 'solo' or 'pool'")
        
        if config['mining_mode'] == 'pool' and 'pool_address' not in config:
            raise ValueError("pool_address is required for pool mining")
    
    def initialize(self):
        """Initialize the miner - check for xmrig and setup config"""
        # Check if xmrig is installed
        xmrig_was_just_installed = False
        
        if not self.check_xmrig_installed():
            print("\n" + "="*60)
            print("XMRig Not Detected")
            print("="*60)
            print("\nXMRig mining software is not installed.")
            
            # Try to install
            if not self.download_and_install_xmrig():
                print("\nPlease install XMRig manually and try again.")
                sys.exit(1)
            
            xmrig_was_just_installed = True
        else:
            print("\nXMRig detected ✓")
        
        # Load or create config
        self.config = self.load_config()
        
        # If config doesn't exist OR xmrig was just installed, setup new config with wallet prompt
        if self.config is None or xmrig_was_just_installed:
            self.config = self.setup_initial_config()
    
    def build_command(self) -> list:
        """Build the XMRig mining command based on configuration"""
        cmd = [self.config.get('miner_executable', 'xmrig')]
        
        # Add wallet address
        wallet = self.config['wallet_address']
        
        # Configure based on mining mode
        if self.config['mining_mode'] == 'solo':
            # Solo mining - connect to local node
            node_addr = self.config.get('node_address', '127.0.0.1:18081')
            cmd.extend(['--daemon', '--daemon-poll-interval=1000'])
            cmd.extend(['--url', node_addr])
            cmd.extend(['--user', wallet])
            print(f"Solo mining mode - connecting to node at {node_addr}")
        else:
            # Pool mining
            pool_addr = self.config['pool_address']
            cmd.extend(['--url', pool_addr])
            cmd.extend(['--user', wallet])
            
            # Add worker name if specified
            worker = self.config.get('worker_name')
            if worker:
                cmd.extend(['--rig-id', worker])
            
            # Pool password
            pool_pass = self.config.get('pool_password', 'x')
            cmd.extend(['--pass', pool_pass])
            
            # TLS
            if self.config.get('tls_enabled', True):
                cmd.append('--tls')
            
            # NiceHash mode
            if self.config.get('nicehash', False):
                cmd.append('--nicehash')
            
            print(f"Pool mining mode - connecting to pool at {pool_addr}")
        
        # CPU Thread configuration
        threads = self.config.get('threads', 0)
        if threads > 0:
            cmd.extend(['--threads', str(threads)])
        
        # CPU max usage
        cpu_max = self.config.get('cpu_max_usage')
        if cpu_max:
            cmd.extend(['--cpu-max-threads-hint', str(cpu_max)])
        
        # Huge pages (not supported on macOS)
        if self.config.get('huge_pages', False) and platform.system() != 'Darwin':
            cmd.append('--hugepages')
        
        # RandomX mode
        rx_mode = self.config.get('randomx_mode', 'auto')
        if rx_mode in ['light', 'fast']:
            cmd.extend(['--randomx-mode', rx_mode])
        
        # MSR MOD for performance optimization
        if self.config.get('msr_mod', False):
            cmd.append('--randomx-wrmsr')
            print("MSR MOD enabled for optimized performance")
        
        # API port for monitoring
        api_port = self.config.get('api_port', 0)
        if api_port > 0:
            cmd.extend(['--http-port', str(api_port)])
            cmd.append('--http-enabled')
        
        # Donate level
        donate = self.config.get('donate_level', 1)
        cmd.extend(['--donate-level', str(donate)])
        
        # Add any extra arguments
        extra_args = self.config.get('extra_args', [])
        if extra_args:
            cmd.extend(extra_args)
        
        return cmd
    
    def start_mining(self):
        """Start the mining process"""
        cmd = self.build_command()
        
        # Check if MSR is enabled but not running with proper privileges
        if self.config.get('msr_mod', False):
            os_type = self.detect_os()
            if os_type == 'linux' and os.geteuid() != 0:
                print("\n" + "="*60)
                print("⚠ WARNING: MSR MOD ENABLED BUT NOT RUNNING AS ROOT")
                print("="*60)
                print("MSR modifications require root privileges on Linux.")
                print("Please restart the miner with sudo:")
                print(f"  sudo python3 {sys.argv[0]}")
                print("\nContinuing anyway (MSR features will be disabled)...")
                print("="*60 + "\n")
                time.sleep(3)
            elif os_type == 'windows' and not self.check_windows_admin():
                print("\n" + "="*60)
                print("⚠ WARNING: MSR MOD ENABLED BUT NOT RUNNING AS ADMINISTRATOR")
                print("="*60)
                print("MSR modifications require Administrator privileges on Windows.")
                print("Please restart this script as Administrator:")
                print("  1. Right-click Command Prompt or PowerShell")
                print("  2. Select 'Run as Administrator'")
                print(f"  3. Run: python {sys.argv[0]}")
                print("\nContinuing anyway (MSR features will be disabled)...")
                print("="*60 + "\n")
                time.sleep(3)
        
        print("\n" + "="*60)
        print("Monero Miner Starting")
        print("="*60)
        print(f"Wallet: {self.config['wallet_address'][:20]}...{self.config['wallet_address'][-10:]}")
        print(f"Mode: {self.config['mining_mode'].upper()}")
        print(f"Platform: {platform.system()} ({platform.machine()})")
        print(f"Command: {' '.join(cmd)}")
        print("="*60 + "\n")
        
        # Setup logging if specified
        log_file = self.config.get('log_file')
        log_handle = None
        
        try:
            if log_file:
                log_handle = open(log_file, 'a')
                log_handle.write(f"\n{'='*60}\n")
                log_handle.write(f"Mining started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                log_handle.write(f"Command: {' '.join(cmd)}\n")
                log_handle.write(f"{'='*60}\n\n")
                log_handle.flush()
            
            # Start the miner process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE if log_handle else None,
                stderr=subprocess.STDOUT if log_handle else None,
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor output if logging
            if log_handle and self.process.stdout:
                try:
                    for line in self.process.stdout:
                        print(line, end='')
                        log_handle.write(line)
                        log_handle.flush()
                except KeyboardInterrupt:
                    print("\n\nReceived interrupt signal. Stopping miner...")
                    self.stop_mining()
            else:
                # Wait for process to complete
                self.process.wait()
                
        except FileNotFoundError:
            print(f"\nError: Miner executable '{cmd[0]}' not found.")
            print("\nPlease ensure XMRig is properly installed.")
            sys.exit(1)
        except Exception as e:
            print(f"Error starting miner: {e}")
            sys.exit(1)
        finally:
            if log_handle:
                log_handle.close()
    
    def stop_mining(self):
        """Stop the mining process"""
        if self.process:
            print("Stopping miner...")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("Force killing miner process...")
                self.process.kill()
            print("Miner stopped.")
    
    def show_stats(self):
        """Display mining statistics if API is enabled"""
        api_port = self.config.get('api_port', 0)
        if api_port > 0:
            print(f"\nMining stats available at: http://127.0.0.1:{api_port}")
            print("You can view real-time statistics in your browser")

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    print("\n\nShutdown signal received...")
    sys.exit(0)

def main():
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    config_file = "miner-monero.json"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    # Create miner instance
    miner = MoneroMiner(config_file)
    
    try:
        # Initialize (check xmrig, setup config)
        miner.initialize()
        
        # Show stats info and start mining
        miner.show_stats()
        miner.start_mining()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        miner.stop_mining()
    except Exception as e:
        print(f"\nError: {e}")
        if miner.process:
            miner.stop_mining()
        sys.exit(1)

if __name__ == "__main__":
    main()
