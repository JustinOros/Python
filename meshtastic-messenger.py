#!/usr/bin/env python3
# Description: Meshtastic Bluetooth Messenger (CLI) - Connect to and message via Meshtastic radios
# Usage: python3 meshtastic-messenger.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import sys
import os                     # ← added
import time
import argparse
import signal                 # ← added
import atexit                 # ← added
import threading              # ← added
from datetime import datetime, timedelta

import meshtastic.serial_interface
try:
    import meshtastic.ble_interface
    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False


class MeshtasticCLI:
    """CLI wrapper around the Meshtastic Python library."""

    def __init__(self, debug_mode=False):
        self.interface = None
        self.nodes = {}
        self.messages = []
        self.exit_flag = False
        self.selected_node = None
        self.debug_mode = debug_mode
        self.current_mode = "node_selection"      # "node_selection" or "messaging"

    # ------------------------------------------------------------------------
    #  EXIT / CLEAN‑UP HELPERS
    # ------------------------------------------------------------------------
    def _close_interface(self):
        """Close the Meshtastic interface without blocking forever."""
        if not self.interface:
            return
        try:
            # Run ``close()`` in its own thread and give it a few seconds.
            # If the library hangs we simply give up – the process will be
            # terminated immediately after this call.
            close_thread = threading.Thread(target=self.interface.close,
                                            daemon=True)
            close_thread.start()
            close_thread.join(timeout=3)          # ← 3 s timeout (adjustable)
        except Exception as e:                    # pragma: no cover
            if self.debug_mode:
                print(f"[DEBUG] error while closing interface: {e}")
        finally:
            self.interface = None

    def _cleanup(self):
        """Registered with ``atexit`` – guarantees the interface is closed."""
        self._close_interface()

    def setup_exit_handler(self):
        """Install SIGINT / SIGTERM handlers and atexit cleanup."""
        # Catch Ctrl‑C from anywhere in the program.
        signal.signal(signal.SIGINT, lambda s, f: self.exit_program())
        # Catch termination from the OS (e.g. `kill`).
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, lambda s, f: self.exit_program())
        # Ensure a final cleanup runs even if we call ``sys.exit`` elsewhere.
        atexit.register(self._cleanup)

    def exit_program(self):
        """Graceful termination used by `/quit` and signal handlers."""
        # Prevent duplicate printing if we get called twice.
        if self.exit_flag:
            return
        print("\n\nExiting...")
        self.exit_flag = True
        self._close_interface()
        # ``os._exit`` stops the interpreter immediately – it does NOT
        # execute ``finally`` blocks or other atexit handlers, which is exactly
        # what we want when background threads misbehave.
        os._exit(0)

    # ------------------------------------------------------------------------
    #  INTERACTION METHODS (unchanged apart from exiting via exit_program)
    # ------------------------------------------------------------------------
    def scan_radios(self):
        """Scan for nearby Meshtastic radios via Bluetooth."""
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
                    has_emoji = any(ord(c) > 127 for c in name)   # simple emoji detection
                    if (name and (
                        'meshtastic' in name.lower() or
                        name.startswith('!') or
                        'mesh' in name.lower() or
                        name.startswith('Meshtastic') or
                        (has_emoji and len(name) <= 10 and '_' in name)
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
        """Prompt user to select and connect to a radio."""
        while True:
            try:
                choice = input("\nEnter number to connect ('r' to retry, 'q' to quit): ").strip()
                if choice.lower() == 'q':
                    self.exit_program()               # ← changed
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
        """Callback for received packets."""
        if self.debug_mode:
            print(f"\n[DEBUG] Packet received: {packet.keys() if isinstance(packet, dict) else type(packet)}")

        try:
            # Store node info
            if 'from' in packet:
                node_id = packet['from']
                node_short_id = f"!{node_id:08x}"

                # Get the best available name
                if 'fromId' in packet and packet['fromId']:
                    node_name = packet['fromId']
                else:
                    node_name = node_short_id
                    if hasattr(self.interface, 'nodesByNum') and node_id in self.interface.nodesByNum:
                        node_info = self.interface.nodesByNum[node_id]
                        user_info = node_info.get('user', {})
                        if 'longName' in user_info and user_info['longName']:
                            node_name = user_info['longName']
                        elif 'shortName' in user_info and user_info['shortName']:
                            node_name = user_info['shortName']

                if node_id not in self.nodes:
                    self.nodes[node_id] = {
                        'id': node_id,
                        'last_seen': datetime.now(),
                        'name': node_name,
                        'short_id': node_short_id
                    }
                else:
                    self.nodes[node_id]['last_seen'] = datetime.now()
                    if 'fromId' in packet and packet['fromId']:
                        self.nodes[node_id]['name'] = packet['fromId']

            # Store and display messages
            if 'decoded' in packet:
                decoded = packet['decoded']
                if self.debug_mode:
                    print(f"[DEBUG] Decoded packet: portnum={decoded.get('portnum')}, has text={('text' in decoded)}")

                # Check if it's a text message
                if (decoded.get('portnum') == 'TEXT_MESSAGE_APP' or
                    decoded.get('portnum') == 1 or
                    'text' in decoded):

                    # Extract text – handle both string and bytes
                    text_content = decoded.get('text', '')
                    if isinstance(text_content, bytes):
                        text_content = text_content.decode('utf-8', errors='ignore')
                    if not text_content and 'payload' in decoded:
                        payload = decoded['payload']
                        if isinstance(payload, bytes):
                            text_content = payload.decode('utf-8', errors='ignore')
                        elif isinstance(payload, dict):
                            text_content = payload.get('text', '')

                    if text_content:
                        from_name = packet.get('fromId', 'Unknown')
                        from_short = f"!{packet.get('from', 0):08x}"
                        to_name = packet.get('toId', 'Broadcast')
                        to_short = (f"!{packet.get('to', 0):08x}"
                                    if packet.get('to') != 0xffffffff else 'Broadcast')

                        msg = {
                            'from': from_name,
                            'from_short': from_short,
                            'to': to_name,
                            'to_short': to_short,
                            'text': text_content,
                            'time': datetime.now()
                        }
                        self.messages.append(msg)
                        # Print new messages in real‑time
                        if self.current_mode == "messaging":
                            time_str = msg['time'].strftime('%Y-%m-%d %H:%M:%S')
                            print(f"\n[{time_str}] {msg['from']} ({msg['from_short']}) -> "
                                  f"{msg['to']} ({msg['to_short']}): {msg['text']}")
                            print("> ", end='', flush=True)
        except Exception as e:
            if self.debug_mode:
                print(f"[DEBUG] Error processing packet: {e}")

    def list_recent_nodes(self):
        """List nodes seen in the last hour."""
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_nodes = {k: v for k, v in self.nodes.items()
                       if v['last_seen'] > one_hour_ago}

        if not recent_nodes:
            print("\nNo nodes detected in the last hour.")
            print("Waiting for node activity...")
            return None

        print(f"\nActive Nodes (Seen in the last hour) ({len(recent_nodes)}):")
        node_list = list(recent_nodes.values())
        node_list.sort(key=lambda x: x['last_seen'], reverse=True)

        for i, node in enumerate(node_list, 1):
            minutes_ago = (datetime.now() - node['last_seen']).seconds // 60
            displayed = node['name'] if node['name'] and node['name'] != node['short_id'] else node['short_id']
            print(f"  {i}. {displayed} (seen {minutes_ago}m ago)")
        return node_list

    def select_contact(self, node_list):
        """Prompt user to select a contact."""
        while True:
            try:
                choice = input("\nEnter number to message ('r' to refresh, 'b' for broadcast, 'q' to quit): ").strip()
                if choice.lower() == 'q':
                    self.exit_program()               # ← changed
                elif choice.lower() == 'b':
                    self.selected_node = None
                    print("Broadcasting to all nodes")
                    return True
                elif choice.lower() == 'r':
                    return False  # refresh

                idx = int(choice) - 1
                if 0 <= idx < len(node_list):
                    self.selected_node = node_list[idx]
                    display_name = (self.selected_node['name']
                                    if self.selected_node['name'] and self.selected_node['name'] != self.selected_node['short_id']
                                    else self.selected_node['short_id'])
                    print(f"Messaging: {display_name}")
                    return True
                else:
                    print("Invalid selection. Try again.")
            except ValueError:
                print("Please enter a valid number.")

    def display_messages(self):
        """Display all past messages."""
        if not self.messages:
            print("\nNo messages yet.")
            return
        print(f"\n--- Message History ({len(self.messages)} messages) ---")
        for msg in self.messages[-20:]:
            t = msg['time'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{t}] {msg['from']} ({msg['from_short']}) -> {msg['to']} ({msg['to_short']}): {msg['text']}")
        print("--- End of messages ---\n")

    def send_message(self, text):
        """Send a message."""
        try:
            time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if self.selected_node:
                # Direct message
                self.interface.sendText(text, destinationId=self.selected_node['id'])
                display_name = (self.selected_node['name']
                                 if self.selected_node['name'] and self.selected_node['name'] != self.selected_node['short_id']
                                 else self.selected_node['short_id'])
                to_display = f"{display_name} ({self.selected_node['short_id']})"
                print(f"[{time_str}] You -> {to_display}: {text}")
            else:
                # Broadcast
                self.interface.sendText(text)
                print(f"[{time_str}] You -> Broadcast: {text}")
        except Exception as e:
            print(f"Failed to send message: {e}")

    def message_loop(self):
        """Main messaging loop."""
        print("\n=== Messaging Interface ===")
        print("Type your message and press ENTER to send")
        print("Type /back to return to node selection")
        print("Type /quit to exit\n")

        while not self.exit_flag:
            try:
                msg = input("> ").strip()

                # Special commands
                if msg.lower() == '/quit':
                    self.exit_program()               # ← changed (os._exit will stop everything)
                elif msg.lower() == '/back':
                    print("\nReturning to node selection...\n")
                    self.current_mode = "node_selection"
                    return False  # go back to node selection

                if msg:
                    self.send_message(msg)

            except KeyboardInterrupt:
                self.exit_program()                       # ← changed
            except EOFError:
                self.exit_program()                       # ← changed

        # The loop only exits when ``self.exit_flag`` is True – which only happens via
        # ``exit_program`` and therefore never reaches the code below.
        # Keeping it for completeness (no‑op if we already exited).
        self._close_interface()
        return True

    # ------------------------------------------------------------------------
    #  MAIN PROGRAM FLOW
    # ------------------------------------------------------------------------
    def run(self):
        """Main program flow."""
        self.setup_exit_handler()
        try:
            # ------------------------------------------------------------
            # Step 1 – scan for radios (with refresh option)
            # ------------------------------------------------------------
            while True:
                devices = self.scan_radios()
                if not devices:
                    print("\nNo devices found. Press Enter to scan again, or 'q' to quit: ", end='')
                    choice = input().strip().lower()
                    if choice == 'q':
                        return
                    continue

                # --------------------------------------------------------
                # Step 2 – connect to a radio (with refresh option)
                # --------------------------------------------------------
                connection_result = self.connect_radio(devices)
                if connection_result is None:   # user asked for a refresh
                    continue
                elif connection_result:
                    break                      # successfully connected
                else:
                    print("\nConnection failed. Press Enter to try again, or 'q' to quit: ", end='')
                    choice = input().strip().lower()
                    if choice == 'q':
                        return

            # ------------------------------------------------------------
            # Step 3 – set up packet receive callback
            # ------------------------------------------------------------
            print("Setting up message listener...")
            callback_set = False

            try:
                # Newer Meshtastic versions use pub/sub
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
                # Old callback API
                try:
                    self.interface.addReceiveCallback(self.on_receive)
                    print("✓ Message listener active (callback)")
                    callback_set = True
                except AttributeError:
                    print("⚠ Warning: Could not set up message callback.")

            # ------------------------------------------------------------
            # Step 4 – give the radio time to sync & pull its node database
            # ------------------------------------------------------------
            print("\nDiscovering nodes and syncing data...")
            print("This may take 10‑20 seconds...\n")

            try:
                if hasattr(self.interface, 'nodesByNum'):
                    for node_id, node_info in self.interface.nodesByNum.items():
                        user = node_info.get('user', {})
                        long_name = user.get('longName', '')
                        short_name = user.get('shortName', '')
                        display_name = long_name or short_name or f"!{node_id:08x}"
                        last_seen = datetime.now()
                        if node_info.get('lastHeard'):
                            try:
                                last_seen = datetime.fromtimestamp(node_info['lastHeard'])
                            except Exception:
                                pass
                        self.nodes[node_id] = {
                            'id': node_id,
                            'last_seen': last_seen,
                            'name': display_name,
                            'short_id': f"!{node_id:08x}",
                            'long_name': long_name,
                            'short_name': short_name
                        }
                    print(f"Loaded {len(self.nodes)} nodes from radio memory")
            except Exception as e:
                if self.debug_mode:
                    print(f"Note: Could not load node database: {e}")

            time.sleep(10)   # give the receive thread a chance to pick up any pending msgs

            # ------------------------------------------------------------
            # Main UI loop – switch between node‑selection and messaging
            # ------------------------------------------------------------
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
                        continue                                   # refresh node list
                elif self.current_mode == "messaging":
                    should_exit = self.message_loop()
                    if should_exit:
                        break                                      # (will never be reached – exit_program kills the process)
                    # If we get here the user typed /back → loop again in node_selection
        finally:
            # ----------------------------------------------------------------
            # ALWAYS clean up the interface – even if we never called exit_program
            # ----------------------------------------------------------------
            self._cleanup()


# --------------------------------------------------------------------
#  Entry‑point
# --------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Meshtastic Bluetooth CLI Messenger')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable debug mode to see packet information')
    args = parser.parse_args()

    try:
        cli = MeshtasticCLI(debug_mode=args.debug)
        cli.run()
    except KeyboardInterrupt:
        # If the user hits Ctrl‑C before we have installed our signal handler
        # we still want a clean shutdown.
        print("\n\nExiting...")
        cli._cleanup()
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

