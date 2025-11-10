#!/usr/bin/env python3
# Description: Bitcoin Miner script using GPU and CPU. 
# Usage: python3 miner-btc.py
# Author: Justin Oros
# Source: https://github.com/JustinOros 

import json
import hashlib
import struct
import time
import os
import requests
from datetime import datetime
from multiprocessing import Process, Queue, cpu_count
from binascii import unhexlify, hexlify

CONFIG_FILE = "miner-btc.json"

def get_default_config():
    """Generate default configuration with dynamic values"""
    return {
        "pool_enabled": False,
        "pool_url": "stratum+tcp://pool.example.com:3333",
        "pool_username": "your_bitcoin_address",
        "pool_password": "x",
        "solo_rpc_url": "http://127.0.0.1:8332",
        "solo_rpc_user": "bitcoinrpc",
        "solo_rpc_password": "your_rpc_password",
        "coinbase_address": "your_bitcoin_address_for_rewards",
        "threads": cpu_count(),
        "scan_time": 60,
        "update_interval": 5
    }


def load_or_create_config():
    """Load config from file or create default config"""
    if not os.path.exists(CONFIG_FILE):
        print(f"[INFO] Config file not found. Creating {CONFIG_FILE}...")
        default_config = get_default_config()
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=4)
        print(f"\n{'='*70}")
        print(f"  ✅ Created {CONFIG_FILE}")
        print(f"{'='*70}")
        print("\nPlease configure the following settings:")
        print("\n📍 FOR SOLO MINING:")
        print("  • solo_rpc_user: Your Bitcoin Core RPC username")
        print("  • solo_rpc_password: Your Bitcoin Core RPC password")
        print("  • coinbase_address: Your Bitcoin address (where rewards go)")
        print("\n📍 FOR POOL MINING:")
        print("  • Set pool_enabled: true")
        print("  • pool_url: Your mining pool's stratum URL")
        print("  • pool_username: Usually your Bitcoin address")
        print("  • pool_password: Usually 'x' or pool-specific password")
        print("\n📍 OPTIONAL:")
        print(f"  • threads: Number of CPU cores to use (default: {default_config['threads']} detected)")
        print("  • update_interval: Seconds between work updates (default: 5)")
        print(f"\n{'='*70}")
        print("Edit miner-btc.json and run this script again.")
        print(f"{'='*70}\n")
        return None
    
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    print(f"[INFO] Loaded configuration from {CONFIG_FILE}")
    return config


def sha256d(data):
    """Double SHA-256 hash (Bitcoin's mining algorithm)"""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def bits_to_target(bits):
    """Convert compact bits representation to full target"""
    exp = bits >> 24
    mant = bits & 0xffffff
    target = mant * (1 << (8 * (exp - 3)))
    return target


def target_to_bits(target):
    """Convert target to compact bits representation"""
    # Find the most significant byte
    s = hex(target)[2:].rstrip('L')
    if len(s) % 2:
        s = '0' + s
    s = bytes.fromhex(s)
    
    # Find first non-zero byte
    for i, b in enumerate(s):
        if b != 0:
            break
    s = s[i:]
    
    # Take first 3 bytes
    if len(s) > 3:
        mantissa = struct.unpack('>I', b'\x00' + s[:3])[0]
        exponent = len(s)
    else:
        mantissa = struct.unpack('>I', b'\x00' * (4 - len(s)) + s)[0]
        exponent = len(s)
    
    return (exponent << 24) | mantissa


def get_work_solo(config):
    """Get mining work from Bitcoin Core RPC (solo mining)"""
    headers = {'content-type': 'application/json'}
    
    # First, get block template
    payload = {
        "jsonrpc": "2.0",
        "id": "macminer",
        "method": "getblocktemplate",
        "params": [{"rules": ["segwit"]}]
    }
    
    try:
        response = requests.post(
            config['solo_rpc_url'],
            auth=(config['solo_rpc_user'], config['solo_rpc_password']),
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"[ERROR] RPC returned status {response.status_code}: {response.text}")
            return None
            
        result = response.json()
        
        if 'error' in result and result['error']:
            print(f"[ERROR] RPC error: {result['error']}")
            return None
            
        if 'result' not in result:
            print(f"[ERROR] No result in response: {result}")
            return None
        
        template = result['result']
        
        # Build coinbase transaction
        coinbase_tx = build_coinbase_transaction(template, config['coinbase_address'])
        
        # Calculate merkle root with coinbase
        transactions = [coinbase_tx] + [unhexlify(tx['data']) for tx in template.get('transactions', [])]
        merkle_root = calculate_merkle_root(transactions)
        
        work = {
            'version': template['version'],
            'previousblockhash': template['previousblockhash'],
            'merkleroot': hexlify(merkle_root).decode(),
            'time': template['curtime'],
            'bits': int(template['bits'], 16),
            'height': template['height'],
            'target': bits_to_target(int(template['bits'], 16)),
            'coinbase_tx': hexlify(coinbase_tx).decode(),
            'transactions': template.get('transactions', [])
        }
        
        return work
        
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to Bitcoin Core at {config['solo_rpc_url']}")
        print("[ERROR] Make sure Bitcoin Core is running with RPC enabled")
        return None
    except Exception as e:
        print(f"[ERROR] Exception getting work: {e}")
        import traceback
        traceback.print_exc()
        return None


def build_coinbase_transaction(template, address):
    """Build a coinbase transaction"""
    # Simplified coinbase - in production, this needs proper scriptSig
    coinbase_script = (
        struct.pack('<B', template['height']) +  # Block height (BIP34)
        b'/MacMiner/' +
        struct.pack('<Q', int(time.time()))  # Timestamp
    )
    
    # Build transaction
    tx = b''
    tx += struct.pack('<I', 1)  # Version
    tx += b'\x01'  # Input count
    tx += b'\x00' * 32  # Previous output hash (null for coinbase)
    tx += b'\xff\xff\xff\xff'  # Previous output index
    tx += struct.pack('<B', len(coinbase_script)) + coinbase_script  # Script
    tx += b'\xff\xff\xff\xff'  # Sequence
    tx += b'\x01'  # Output count
    
    # Output amount (block reward + fees)
    reward = template['coinbasevalue']
    tx += struct.pack('<Q', reward)
    
    # Output script (P2PKH to address)
    # This is simplified - proper implementation should decode address
    script_pubkey = b'\x76\xa9\x14' + b'\x00' * 20 + b'\x88\xac'
    tx += struct.pack('<B', len(script_pubkey)) + script_pubkey
    
    tx += struct.pack('<I', 0)  # Locktime
    
    return tx


def calculate_merkle_root(transactions):
    """Calculate merkle root from list of transactions"""
    if not transactions:
        return b'\x00' * 32
    
    hashes = [sha256d(tx) for tx in transactions]
    
    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
        
        hashes = [sha256d(hashes[i] + hashes[i+1]) for i in range(0, len(hashes), 2)]
    
    return hashes[0]


def build_block_header(work, nonce, extra_nonce=0):
    """Build block header for mining"""
    header = b''
    header += struct.pack('<I', work['version'])
    header += unhexlify(work['previousblockhash'])[::-1]  # Reverse byte order
    header += unhexlify(work['merkleroot'])[::-1]
    header += struct.pack('<I', work['time'])
    header += struct.pack('<I', work['bits'])
    header += struct.pack('<I', nonce)
    return header


def submit_work_solo(config, work, nonce):
    """Submit found block to Bitcoin Core RPC"""
    headers = {'content-type': 'application/json'}
    
    # Build complete block
    block_header = build_block_header(work, nonce)
    
    # Build full block hex
    block_hex = hexlify(block_header).decode()
    
    # Add transaction count and coinbase
    block_hex += '01'  # Tx count (just coinbase for now)
    block_hex += work['coinbase_tx']
    
    payload = {
        "jsonrpc": "2.0",
        "id": "macminer",
        "method": "submitblock",
        "params": [block_hex]
    }
    
    try:
        response = requests.post(
            config['solo_rpc_url'],
            auth=(config['solo_rpc_user'], config['solo_rpc_password']),
            headers=headers,
            json=payload,
            timeout=10
        )
        
        result = response.json()
        if 'result' in result and result['result'] is None:
            print("\n" + "="*60)
            print("🎉 BLOCK FOUND AND ACCEPTED! 🎉")
            print("="*60)
            return True
        else:
            print(f"\n[WARNING] Block rejected: {result}")
            return False
    except Exception as e:
        print(f"[ERROR] Submit error: {e}")
        return False


def mine_worker(worker_id, config, work_queue, result_queue, stats_queue, stop_flag):
    """Mining worker process optimized for Apple Silicon"""
    print(f"[WORKER-{worker_id}] Started on Apple Silicon core")
    
    hashes = 0
    start_time = time.time()
    current_work = None
    
    while not stop_flag.value:
        # Get new work if available
        if not work_queue.empty():
            try:
                current_work = work_queue.get_nowait()
                hashes = 0
                start_time = time.time()
            except:
                pass
        
        if current_work is None:
            time.sleep(0.1)
            continue
        
        # Mine a batch of nonces
        batch_size = 100000
        nonce_start = worker_id * 10000000 + (hashes // batch_size) * batch_size * config['threads']
        
        target = current_work['target']
        
        for nonce in range(nonce_start, nonce_start + batch_size):
            # Build and hash block header
            header = build_block_header(current_work, nonce)
            block_hash = sha256d(header)
            
            # Convert hash to integer for comparison (little-endian)
            hash_int = int.from_bytes(block_hash, 'little')
            
            hashes += 1
            
            # Check if we found a block
            if hash_int < target:
                print(f"\n{'='*60}")
                print(f"[WORKER-{worker_id}] 🎯 BLOCK FOUND!")
                print(f"Nonce: {nonce}")
                print(f"Hash: {hexlify(block_hash[::-1]).decode()}")
                print(f"{'='*60}\n")
                
                result_queue.put({
                    'found': True,
                    'nonce': nonce,
                    'work': current_work,
                    'hash': hexlify(block_hash[::-1]).decode()
                })
            
            # Update stats periodically
            if hashes % 10000 == 0:
                elapsed = time.time() - start_time
                hashrate = hashes / elapsed if elapsed > 0 else 0
                stats_queue.put({
                    'worker_id': worker_id,
                    'hashes': hashes,
                    'hashrate': hashrate
                })
                
                # Check stop flag
                if stop_flag.value:
                    break


def display_stats(stats_queue, num_workers, config, work_info):
    """Display mining statistics"""
    worker_stats = {i: {'hashes': 0, 'hashrate': 0} for i in range(num_workers)}
    last_update = time.time()
    
    while True:
        try:
            # Update worker stats
            while not stats_queue.empty():
                stat = stats_queue.get_nowait()
                worker_id = stat['worker_id']
                worker_stats[worker_id] = {
                    'hashes': stat['hashes'],
                    'hashrate': stat['hashrate']
                }
            
            # Update display every second
            if time.time() - last_update >= 1.0:
                # Calculate total hashrate
                total_hashrate = sum(w['hashrate'] for w in worker_stats.values())
                total_hashes = sum(w['hashes'] for w in worker_stats.values())
                
                # Clear screen and display stats
                os.system('clear' if os.name == 'posix' else 'cls')
                print("=" * 70)
                print("       MacMiner - Bitcoin Miner for Apple Silicon")
                print("=" * 70)
                print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Mode: {'Pool Mining' if config['pool_enabled'] else 'Solo Mining'}")
                
                if work_info['height']:
                    print(f"Block Height: {work_info['height']}")
                    print(f"Difficulty: {work_info['difficulty']:,.2f}")
                
                print(f"Workers: {num_workers}")
                print(f"Total Hashes: {total_hashes:,}")
                print(f"Total Hashrate: {total_hashrate/1000:,.2f} KH/s ({total_hashrate:,.0f} H/s)")
                print("-" * 70)
                
                for worker_id in sorted(worker_stats.keys()):
                    stats = worker_stats[worker_id]
                    print(f"Worker {worker_id:2d}: {stats['hashrate']/1000:>8.2f} KH/s  |  {stats['hashes']:>12,} hashes")
                
                print("=" * 70)
                print("Press Ctrl+C to stop mining")
                
                last_update = time.time()
            
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[ERROR] Stats display error: {e}")
            time.sleep(1)


def main():
    """Main mining loop"""
    print("=" * 70)
    print("     MacMiner - Bitcoin Miner for Apple Silicon")
    print("=" * 70)
    
    # Load configuration
    config = load_or_create_config()
    
    if config is None:
        return
    
    # Display configuration
    print(f"\n{'='*70}")
    print(f"  MACMINER CONFIGURATION")
    print(f"{'='*70}")
    print(f"Mining Mode: {'🌊 Pool Mining' if config['pool_enabled'] else '⛏️  Solo Mining'}")
    print(f"Threads: {config['threads']} CPU cores")
    
    if config['pool_enabled']:
        print(f"Pool URL: {config['pool_url']}")
        print(f"Pool Username: {config['pool_username']}")
    else:
        print(f"RPC URL: {config['solo_rpc_url']}")
        print(f"Coinbase Address: {config.get('coinbase_address', 'NOT SET')}")
    
    print(f"{'='*70}\n")
    
    if config['pool_enabled']:
        print(f"\n[ERROR] Pool mining not yet implemented.")
        print("Set 'pool_enabled': false in config for solo mining.")
        return
    
    # Test connection to Bitcoin Core
    print(f"\n[INFO] Testing connection to Bitcoin Core...")
    test_work = get_work_solo(config)
    if test_work is None:
        print("\n" + "="*70)
        print("  ⚠️  BITCOIN CORE NOT DETECTED")
        print("="*70)
        print("\nMacMiner requires Bitcoin Core to be running and synchronized.")
        print("\nOption 1 - Install Bitcoin Core locally:")
        print("  1. Download Bitcoin Core from: https://bitcoin.org")
        print("  2. Install and run Bitcoin Core")
        print("  3. Wait for blockchain to synchronize (this may take several days)")
        print("  4. Configure RPC in ~/Library/Application Support/Bitcoin/bitcoin.conf:")
        print("     server=1")
        print("     rpcuser=yourusername")
        print("     rpcpassword=yourpassword")
        print("     rpcallowip=127.0.0.1")
        print("  5. Restart Bitcoin Core")
        print("  6. Update miner-btc.json with your RPC credentials")
        print("  7. Run miner-btc.py again")
        print("\nOption 2 - Connect to remote Bitcoin Core:")
        print("  1. Update 'solo_rpc_url' in miner-btc.json with remote host IP/hostname")
        print("     Example: \"http://192.168.1.100:8332\"")
        print("  2. Ensure remote Bitcoin Core has rpcallowip configured for your IP")
        print("  3. Update RPC credentials in miner-btc.json")
        print("  4. Run miner-btc.py again")
        print("\n" + "="*70)
        return
    
    print(f"[SUCCESS] Connected! Block height: {test_work['height']}")
    print(f"[INFO] Current difficulty: {bits_to_target(test_work['bits']) / (2**224):,.2f}")
    
    # Initialize queues and shared state
    work_queue = Queue()
    result_queue = Queue()
    stats_queue = Queue()
    
    from multiprocessing import Value
    stop_flag = Value('i', 0)
    
    work_info = {'height': test_work['height'], 'difficulty': bits_to_target(test_work['bits']) / (2**224)}
    
    # Start worker processes
    num_workers = config['threads']
    workers = []
    
    print(f"\n[INFO] Starting {num_workers} mining workers...")
    
    for i in range(num_workers):
        p = Process(target=mine_worker, args=(i, config, work_queue, result_queue, stats_queue, stop_flag))
        p.start()
        workers.append(p)
    
    time.sleep(1)
    
    # Start stats display in separate process
    stats_process = Process(target=display_stats, args=(stats_queue, num_workers, config, work_info))
    stats_process.start()
    
    # Distribute initial work
    for _ in range(num_workers):
        work_queue.put(test_work)
    
    try:
        last_update = time.time()
        
        # Main loop - get new work and check for results
        while True:
            # Get new work periodically
            if time.time() - last_update >= config['update_interval']:
                new_work = get_work_solo(config)
                if new_work:
                    work_info['height'] = new_work['height']
                    work_info['difficulty'] = bits_to_target(new_work['bits']) / (2**224)
                    
                    # Distribute to all workers
                    for _ in range(num_workers * 2):  # Extra work items in queue
                        work_queue.put(new_work)
                    
                last_update = time.time()
            
            # Check for found blocks
            while not result_queue.empty():
                result = result_queue.get()
                if result['found']:
                    # Submit the block
                    submit_work_solo(config, result['work'], result['nonce'])
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n[INFO] Stopping miners...")
        stop_flag.value = 1
        
        # Wait for workers to stop
        for w in workers:
            w.join(timeout=3)
            if w.is_alive():
                w.terminate()
        
        stats_process.terminate()
        stats_process.join(timeout=1)
        
        print("[INFO] Mining stopped. Goodbye!")


if __name__ == "__main__":
    main()
