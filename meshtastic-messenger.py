#!/usr/bin/env python3
# Description: Meshtastic Bluetooth Messenger (CLI) - Connect to and message via Meshtastic radios
# Usage: python3 meshtastic-messenger.py
# Author: Justin Oros
# Source: https://github.com/JustinOros 

import sys
import time
import argparse
from datetime import datetime, timedelta
import meshtastic.serial_interface
try:
    import meshtastic.ble_interface
    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False

class MeshtasticCLI:
    def __init__(self, debug_mode=False):
        self.interface = None
        self.nodes = {}
        self.messages = []
        self.exit_flag = False
        self.selected_node = None
        self.debug_mode = debug_mode
        self.current_mode = "node_selection"  # Can be "node_selection" or "messaging"
        
    def setup_exit_handler(self):
        """Setup exit handler"""
        # Exit via /quit command
        pass
    
    def exit_program(self):
        """Exit the program gracefully"""
        print("\n\nExiting...")
        self.exit_flag = True
        if self.interface:
            try:
                self.interface.close()
            except:
                pass
        sys.exit(0)
    
    def scan_radios(self):
        """Scan for nearby Meshtastic radios via Bluetooth"""
        print("Scanning for Meshtastic radios via Bluetooth (10 seconds)...")
        print("Make sure your radio's Bluetooth is enabled!\n")
        
        try:
            import asyncio
            from bleak import BleakScanner
            
            async def scan():
                print("Scanning all Bluetooth devices...")
                devices = await BleakScanner.discover(timeout=10.0)
                
                if self.debug_mode:
                    print(f"\nFound {len(devices)} total Bluetooth devices")
                    print("\nAll devices (for debugging):")
                    for d in devices:
                        print(f"  - {d.name or 'Unknown'} ({d.address})")
                
                # Filter for Meshtastic devices (very permissive)
                meshtastic_devices = []
                for d in devices:
                    name = d.name or ""
                    # Match Meshtastic patterns including emoji prefixes
                    # Common Meshtastic emojis: 📡 🏠 🚀 🌐 📻 and others
                    has_emoji = any(ord(c) > 127 for c in name)  # Simple emoji detection
                    
                    if (name and (
                        'meshtastic' in name.lower() or 
                        name.startswith('!') or
                        'mesh' in name.lower() or
                        name.startswith('Meshtastic') or
                        (has_emoji and len(name) <= 10 and '_' in name)  # Emoji_XXXX pattern
                    )):
                        meshtastic_devices.append({
                            'name': d.name,
                            'address': d.address
                        })
                
                return meshtastic_devices, devices
            
            meshtastic_devices, all_devices = asyncio.run(scan())
            
            if not meshtastic_devices:
                print("\nNo Meshtastic radios auto-detected.")
                print("Would you like to manually select a device? (y/n): ", end='')
                choice = input().strip().lower()
                
                if choice == 'y':
                    # Let user pick from all devices
                    print("\nAll available devices:")
                    for i, d in enumerate(all_devices, 1):
                        print(f"  {i}. {d.name or 'Unknown'} - {d.address}")
                    
                    return [{'name': d.name or 'Unknown', 'address': d.address} 
                            for d in all_devices]
                return None
            
            print(f"\nFound {len(meshtastic_devices)} Meshtastic radio(s):")
            for i, device in enumerate(meshtastic_devices, 1):
                print(f"  {i}. {device['name']} - {device['address']}")
            
            return meshtastic_devices
            
        except Exception as e:
            print(f"Bluetooth scan error: {e}")
            print("\nTroubleshooting tips:")
            print("  - Ensure Bluetooth is enabled on your computer")
            print("  - Make sure your Meshtastic radio's Bluetooth is on")
            print("  - Try running with sudo on Linux/Mac")
            return None
    
    def connect_radio(self, devices):
        """Prompt user to select and connect to a radio"""
        while True:
            try:
                choice = input("\nEnter number to connect (or 'q' to quit, 'r' to refresh): ").strip()
                if choice.lower() == 'q':
                    sys.exit(0)
                elif choice.lower() == 'r':
                    return None  # Signal to refresh scan
                
                idx = int(choice) - 1
                if 0 <= idx < len(devices):
                    device = devices[idx]
                    print(f"\nConnecting to {device['name']}...")
                    
                    # Try BLE interface
                    if BLE_AVAILABLE:
                        try:
                            self.interface = meshtastic.ble_interface.BLEInterface(device['address'])
                            time.sleep(3)
                            print("Connected via BLE!")
                            return True
                        except Exception as e:
                            print(f"BLE connection failed: {e}")
                            return False
                    else:
                        print("BLE interface not available. Install bleak: pip install bleak")
                        return False
                else:
                    print("Invalid selection. Try again.")
            except ValueError:
                print("Please enter a valid number.")
            except Exception as e:
                print(f"Connection failed: {e}")
                return False
    
    def on_receive(self, packet, interface=None):
        """Callback for received packets"""
        if self.debug_mode:
            print(f"\n[DEBUG] Packet received: {packet.keys() if isinstance(packet, dict) else type(packet)}")
        
        try:
            # Store node info
            if 'from' in packet:
                node_id = packet['from']
                node_short_id = f"!{node_id:08x}"
                node_long_name = packet.get('fromId', node_short_id)
                
                if node_id not in self.nodes:
                    self.nodes[node_id] = {
                        'id': node_id,
                        'last_seen': datetime.now(),
                        'name': node_long_name,
                        'short_id': node_short_id
                    }
                else:
                    self.nodes[node_id]['last_seen'] = datetime.now()
                    if 'fromId' in packet:
                        self.nodes[node_id]['name'] = packet['fromId']
            
            # Store and display messages
            if 'decoded' in packet:
                decoded = packet['decoded']
                if self.debug_mode:
                    print(f"[DEBUG] Decoded packet: portnum={decoded.get('portnum')}, has text={('text' in decoded)}")
                
                # Check if it's a text message
                if (decoded.get('portnum') == 'TEXT_MESSAGE_APP' or 
                    decoded.get('portnum') == 1 or  # TEXT_MESSAGE_APP enum value
                    'text' in decoded):
                    
                    # Extract text - handle both string and bytes
                    text_content = decoded.get('text', '')
                    
                    # If text is bytes, decode it
                    if isinstance(text_content, bytes):
                        text_content = text_content.decode('utf-8', errors='ignore')
                    
                    # If still no text, try payload
                    if not text_content and 'payload' in decoded:
                        payload = decoded.get('payload', '')
                        if isinstance(payload, bytes):
                            text_content = payload.decode('utf-8', errors='ignore')
                        elif isinstance(payload, dict):
                            text_content = payload.get('text', '')
                    
                    if text_content:  # Only store if there's actual text
                        from_name = packet.get('fromId', 'Unknown')
                        from_short = f"!{packet.get('from', 0):08x}"
                        to_name = packet.get('toId', 'Broadcast')
                        to_short = f"!{packet.get('to', 0):08x}" if packet.get('to') != 0xffffffff else 'Broadcast'
                        
                        msg = {
                            'from': from_name,
                            'from_short': from_short,
                            'to': to_name,
                            'to_short': to_short,
                            'text': text_content,
                            'time': datetime.now()
                        }
                        self.messages.append(msg)
                        # Print new messages in real-time
                        if self.current_mode == "messaging":
                            time_str = msg['time'].strftime('%Y-%m-%d %H:%M:%S')
                            print(f"\n[{time_str}] {msg['from']} ({msg['from_short']}) -> {msg['to']} ({msg['to_short']}): {msg['text']}")
                            print("> ", end='', flush=True)
        except Exception as e:
            if self.debug_mode:
                print(f"[DEBUG] Error processing packet: {e}")
    
    def list_recent_nodes(self):
        """List nodes seen in the last hour"""
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_nodes = {k: v for k, v in self.nodes.items() 
                       if v['last_seen'] > one_hour_ago}
        
        if not recent_nodes:
            print("\nNo nodes detected in the last hour.")
            print("Waiting for node activity...")
            return None
        
        print(f"\nActive Nodes (Seen in the last hour) ({len(recent_nodes)}):")
        node_list = list(recent_nodes.values())
        for i, node in enumerate(node_list, 1):
            time_ago = (datetime.now() - node['last_seen']).seconds // 60
            print(f"  {i}. {node['name']} (seen {time_ago}m ago)")
        
        return node_list
    
    def select_contact(self, node_list):
        """Prompt user to select a contact"""
        while True:
            try:
                choice = input("\nEnter number to message (or 'b' for broadcast, 'r' to refresh): ").strip()
                
                if choice.lower() == 'b':
                    self.selected_node = None
                    print("Broadcasting to all nodes")
                    return True
                elif choice.lower() == 'r':
                    return False  # Signal to refresh
                
                idx = int(choice) - 1
                if 0 <= idx < len(node_list):
                    self.selected_node = node_list[idx]
                    print(f"Messaging: {self.selected_node['name']}")
                    return True
                else:
                    print("Invalid selection. Try again.")
            except ValueError:
                print("Please enter a valid number.")
    
    def display_messages(self):
        """Display all past messages"""
        if not self.messages:
            print("\nNo messages yet.")
            return
        
        print(f"\n--- Message History ({len(self.messages)} messages) ---")
        for msg in self.messages[-20:]:  # Show last 20 messages
            time_str = msg['time'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{time_str}] {msg['from']} ({msg['from_short']}) -> {msg['to']} ({msg['to_short']}): {msg['text']}")
        print("--- End of messages ---\n")
    
    def send_message(self, text):
        """Send a message"""
        try:
            time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if self.selected_node:
                # Direct message
                self.interface.sendText(text, destinationId=self.selected_node['id'])
                short_id = self.selected_node.get('short_id', f"!{self.selected_node['id']:08x}")
                to_display = f"{self.selected_node['name']} ({short_id})"
                print(f"[{time_str}] You -> {to_display}: {text}")
            else:
                # Broadcast
                self.interface.sendText(text)
                print(f"[{time_str}] You -> Broadcast: {text}")
        except Exception as e:
            print(f"Failed to send message: {e}")
    
    def message_loop(self):
        """Main messaging loop"""
        print("\n=== Messaging Interface ===")
        print("Type your message and press ENTER to send")
        print("Type /back to return to node selection")
        print("Type /quit to exit\n")
        
        while not self.exit_flag:
            try:
                msg = input("> ").strip()
                
                # Check for special commands
                if msg.lower() == '/quit':
                    self.exit_program()
                    break
                elif msg.lower() == '/back':
                    print("\nReturning to node selection...\n")
                    self.current_mode = "node_selection"
                    return False  # Signal to go back
                
                if self.exit_flag:
                    break
                    
                if msg:
                    self.send_message(msg)
                    
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except EOFError:
                print("\n\nExiting...")
                break
        
        # Clean up
        if self.interface:
            try:
                self.interface.close()
            except:
                pass
        return True  # Signal to exit
    
    def run(self):
        """Main program flow"""
        self.setup_exit_handler()
        
        # Step 1: Scan for radios with refresh option
        while True:
            devices = self.scan_radios()
            if not devices:
                print("\nNo devices found. Press Enter to scan again, or 'q' to quit: ", end='')
                choice = input().strip().lower()
                if choice == 'q':
                    return
                continue
            
            # Step 2: Connect to radio with refresh option
            connection_result = self.connect_radio(devices)
            if connection_result is None:
                # User selected 'r' to refresh
                continue
            elif connection_result:
                break  # Successfully connected
            else:
                # Connection failed
                print("\nConnection failed. Press Enter to try again, or 'q' to quit: ", end='')
                choice = input().strip().lower()
                if choice == 'q':
                    return
        
        # Setup packet callback using the correct method
        print("Setting up message listener...")
        callback_set = False
        
        try:
            # Try the pub/sub method for newer meshtastic versions
            from pubsub import pub
            
            def on_receive_wrapper(packet, interface=None):
                self.on_receive(packet, interface)
            
            pub.subscribe(on_receive_wrapper, "meshtastic.receive")
            print("✓ Message listener active (pub/sub)")
            callback_set = True
        except Exception as e:
            if self.debug_mode:
                print(f"Pub/sub setup failed: {e}")
        
        if not callback_set:
            # Fallback to old callback method
            try:
                self.interface.addReceiveCallback(self.on_receive)
                print("✓ Message listener active (callback)")
                callback_set = True
            except AttributeError:
                print("⚠ Warning: Could not set up message callback.")
        
        # Step 3: Wait for node discovery
        print("\nDiscovering nodes and syncing data...")
        print("This may take 10-20 seconds...\n")
        
        # Get nodedb to populate nodes
        try:
            if hasattr(self.interface, 'nodesByNum'):
                for node_id, node_info in self.interface.nodesByNum.items():
                    self.nodes[node_id] = {
                        'id': node_id,
                        'last_seen': datetime.fromtimestamp(node_info.get('lastHeard', 0)) if node_info.get('lastHeard') else datetime.now(),
                        'name': node_info.get('user', {}).get('longName', f"!{node_id:08x}"),
                        'short_id': f"!{node_id:08x}"
                    }
                print(f"Loaded {len(self.nodes)} nodes from radio memory")
        except Exception as e:
            if self.debug_mode:
                print(f"Note: Could not load node database: {e}")
        
        time.sleep(10)
        
        # Main loop that allows switching between modes
        while not self.exit_flag:
            if self.current_mode == "node_selection":
                node_list = self.list_recent_nodes()
                if node_list is None:
                    time.sleep(5)
                    continue
                
                if self.select_contact(node_list):
                    self.current_mode = "messaging"
                    self.display_messages()
                else:
                    continue  # Refresh node list
            
            elif self.current_mode == "messaging":
                should_exit = self.message_loop()
                if should_exit:
                    break  # Exit program
                # If we get here, user typed /back, so we'll loop again in node_selection mode

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Meshtastic Bluetooth CLI Messenger')
    parser.add_argument('-d', '--debug', action='store_true', 
                        help='Enable debug mode to see packet information')
    args = parser.parse_args()
    
    try:
        cli = MeshtasticCLI(debug_mode=args.debug)
        cli.run()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
