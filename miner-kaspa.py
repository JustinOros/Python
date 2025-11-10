#!/usr/bin/env python3
# Description: Kaspa Mining Script - Supports both solo mining and pool mining with JSON configuration
# Usage: python3 miner-kaspa.py
# Author: Justin Oros
# Source: https://github.com/JustinOros 

import json
import subprocess
import sys
import os
import time
import signal
from pathlib import Path
from typing import Dict, Optional

class KaspaMiner:
    def __init__(self, config_file: str = "miner-kaspa.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.process: Optional[subprocess.Popen] = None
        
    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        if not os.path.exists(self.config_file):
            print(f"Error: Configuration file '{self.config_file}' not found.")
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
        """Create an example configuration file"""
        example_config = {
            "wallet_address": "kaspa:qz1234567890abcdefghijklmnopqrstuvwxyz",
            "mining_mode": "solo",
            "miner_executable": "kaspa-miner",
            "kaspad_address": "127.0.0.1:16110",
            "pool_address": "pool.example.com:5555",
            "worker_name": "worker1",
            "threads": 0,
            "gpu_enable": True,
            "gpu_devices": [0],
            "intensity": 20,
            "extra_args": [],
            "log_file": "kaspa-miner.log"
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(example_config, f, indent=4)
        
        print(f"Created example configuration file: {self.config_file}")
        print("Please edit it with your mining details.")
    
    def build_command(self) -> list:
        """Build the mining command based on configuration"""
        cmd = [self.config.get('miner_executable', 'kaspa-miner')]
        
        # Add wallet address
        cmd.extend(['--mining-address', self.config['wallet_address']])
        
        # Configure based on mining mode
        if self.config['mining_mode'] == 'solo':
            # Solo mining - connect to local kaspad
            kaspad_addr = self.config.get('kaspad_address', '127.0.0.1:16110')
            cmd.extend(['--kaspad-address', kaspad_addr])
            print(f"Solo mining mode - connecting to kaspad at {kaspad_addr}")
        else:
            # Pool mining
            pool_addr = self.config['pool_address']
            cmd.extend(['--pool', pool_addr])
            
            # Add worker name if specified
            worker = self.config.get('worker_name')
            if worker:
                cmd.extend(['--worker-name', worker])
            
            print(f"Pool mining mode - connecting to pool at {pool_addr}")
        
        # Thread configuration
        threads = self.config.get('threads', 0)
        if threads > 0:
            cmd.extend(['--threads', str(threads)])
        
        # GPU configuration
        if self.config.get('gpu_enable', True):
            gpu_devices = self.config.get('gpu_devices', [0])
            if gpu_devices:
                cmd.extend(['--cuda-devices', ','.join(map(str, gpu_devices))])
            
            intensity = self.config.get('intensity')
            if intensity:
                cmd.extend(['--intensity', str(intensity)])
        else:
            cmd.append('--no-cuda')
        
        # Add any extra arguments
        extra_args = self.config.get('extra_args', [])
        if extra_args:
            cmd.extend(extra_args)
        
        return cmd
    
    def start_mining(self):
        """Start the mining process"""
        cmd = self.build_command()
        
        print("\n" + "="*60)
        print("Kaspa Miner Starting")
        print("="*60)
        print(f"Wallet: {self.config['wallet_address']}")
        print(f"Mode: {self.config['mining_mode'].upper()}")
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
            print(f"Error: Miner executable '{cmd[0]}' not found.")
            print("Please ensure the miner is installed and the path is correct.")
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

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    print("\n\nShutdown signal received...")
    sys.exit(0)

def main():
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    config_file = "miner-kaspa.json"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    # Create and start miner
    miner = KaspaMiner(config_file)
    
    try:
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
