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
from pathlib import Path
from typing import Dict, Optional

class MoneroMiner:
    def __init__(self, config_file: str = "miner-monero.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.process: Optional[subprocess.Popen] = None
        
    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        if not os.path.exists(self.config_file):
            print(f"Configuration file '{self.config_file}' not found.")
            print("Creating example configuration file...")
            self.create_example_config()
            sys.exit(1)
            
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
    
    def create_example_config(self):
        """Create an example configuration file with platform-specific defaults"""
        is_mac = platform.system() == 'Darwin'
        is_arm = platform.machine().lower() in ['arm64', 'aarch64']
        
        example_config = {
            "wallet_address": "YOUR_MONERO_WALLET_ADDRESS_HERE",
            "mining_mode": "pool",
            "miner_executable": "xmrig" if not is_mac else "./xmrig",
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
            "extra_args": [],
            "log_file": "monero-miner.log",
            "api_port": 0,
            "donate_level": 1
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(example_config, f, indent=4)
        
        print(f"Created example configuration file: {self.config_file}")
        print("\n" + "="*60)
        print("IMPORTANT: Edit the configuration file and set your wallet!")
        print("="*60)
        if is_mac:
            print("\nFor Mac users:")
            print("1. Download XMRig from: https://github.com/xmrig/xmrig/releases")
            print("2. Extract and place 'xmrig' binary in the same folder as this script")
            print("3. Run: chmod +x xmrig")
        print("\nPopular Monero pools:")
        print("  - SupportXMR: pool.supportxmr.com:443")
        print("  - MoneroOcean: gulf.moneroocean.stream:10128")
        print("  - Nanopool: xmr-us-east1.nanopool.org:14433")
        print("  - MineXMR: pool.minexmr.com:443")
    
    def build_command(self) -> list:
        """Build the XMRig mining command based on configuration"""
        cmd = [self.config.get('miner_executable', 'xmrig')]
        
        # Add wallet address
        wallet = self.config['wallet_address']
        if wallet == "YOUR_MONERO_WALLET_ADDRESS_HERE":
            print("Error: Please set your Monero wallet address in the config file!")
            sys.exit(1)
        
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
            print("\nFor macOS/Apple Silicon:")
            print("1. Download XMRig from: https://github.com/xmrig/xmrig/releases")
            print("2. Look for 'xmrig-X.X.X-macos-arm64.tar.gz' for M2 Mac")
            print("3. Extract and place 'xmrig' in the same folder as this script")
            print("4. Run: chmod +x xmrig")
            print("\nFor Linux:")
            print("  sudo apt install xmrig  # or download from GitHub")
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
    
    # Create and start miner
    miner = MoneroMiner(config_file)
    
    try:
        miner.show_stats()
        miner.start_mining()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        miner.stop_mining()
    except Exception as e:
        print(f"\nError: {e}")
        miner.stop_mining()
        sys.exit(1)

if __name__ == "__main__":
    main()
