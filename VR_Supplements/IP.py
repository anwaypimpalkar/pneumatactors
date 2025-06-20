import socket
import time
import ipaddress
import subprocess
import fcntl
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# Configuration
PORT = 4210
DISCOVERY_MSG = b"DISCOVERXIAO"
EXPECTED_RESPONSE = b"XIAO_HERE"
TIMEOUT = 0.75
SCAN_RANGE = range(0, 255)
MAX_THREADS = 50

def get_local_ip():
    """Get the IP address of the default network interface."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to a public IP (doesn't actually send data)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

def is_host_up(ip):
    """Ping a single IP."""
    try:
        subprocess.check_output(["ping", "-c", "1", "-W", "1", ip],
                                stderr=subprocess.DEVNULL)
        return ip
    except subprocess.CalledProcessError:
        return None

def discover_xiao_devices():
    discovered = []
    responses = {}

    local_ip = get_local_ip()
    subnet_base = '.'.join(local_ip.split('.')[:3])
    subnet_cidr = f"{subnet_base}.0/24"

    # Step 1: Parallel ping
    ips_to_check = [f"{subnet_base}.{i}" for i in SCAN_RANGE]
    print(f"Scanning for alive hosts in {subnet_cidr}...")

    alive_ips = []
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {executor.submit(is_host_up, ip): ip for ip in ips_to_check}
        for future in as_completed(futures):
            result = future.result()
            if result:
                alive_ips.append(result)

    print(f"  ↪ Found {len(alive_ips)} reachable IPs")

    # Step 2: Send DISCOVERXIAO
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(TIMEOUT)
        s.bind(('', PORT))

        for ip in alive_ips:
            try:
                s.sendto(DISCOVERY_MSG, (ip, PORT))
            except OSError:
                continue

        # Step 3: Listen for responses
        start = time.time()
        while time.time() - start < 2:
            try:
                data, addr = s.recvfrom(1024)
                ip = addr[0]
                if data.strip() == EXPECTED_RESPONSE and ip not in discovered:
                    discovered.append(ip)
                    responses[ip] = data.strip().decode()
            except socket.timeout:
                break

    return discovered, responses, subnet_cidr

def print_green(text):
    print(f"\033[92m{text}\033[0m")

def print_red(text):
    print(f"\033[91m{text}\033[0m")

if __name__ == "__main__":
    found, responses, subnet_used = discover_xiao_devices()

    print(f"\nFinished scanning {subnet_used} for Xiao devices.")
    if found:
        print_green(f"\nScan complete on {subnet_used}.")
        print_green(f"Xiao device(s) found:")
        for ip in found:
            print_green(f"  - {ip} : {responses[ip]}")
    else:
        print_red(f"\nScan complete on {subnet_used}.")
        print_red("No Xiao devices responded.")