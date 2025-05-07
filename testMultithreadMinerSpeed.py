import socket
import json
import hashlib
import struct
import time
import multiprocessing
import os
import psutil

def pin_this_process_to_core(core_id):
    p = psutil.Process(os.getpid())
    p.cpu_affinity([core_id]) 

SAVE_PATH = "sample_job.json"

def get_input(prompt, data_type=str):
    while True:
        try:
            value = data_type(input(prompt))
            return value
        except ValueError:
            print(f"Invalid input. Please enter a valid {data_type.__name__}.")

if os.path.isfile('config.json'):
    print("config.json found,start mining")
    with open('config.json','r') as file:
        config = json.load(file)
    pool_address = config['pool_address']
    pool_port = config["pool_port"]
    username = config["user_name"]
    password = config["password"]
    min_diff = config["min_diff"]
else:
    print("config.json doesn't exist,generating now")
    pool_address = get_input("Enter the pool address: ")
    pool_port = get_input("Enter the pool port: ", int)
    user_name = get_input("Enter the user name: ")
    password = get_input("Enter the password: ")
    min_diff = get_input("Enter the minimum difficulty: ", float)
    config_data = {
        "pool_address": pool_address,
        "pool_port": pool_port,
        "user_name": user_name,
        "password": password,
        "min_diff": min_diff
    }
    with open("config.json", "w") as config_file:
        json.dump(config_data, config_file, indent=4)
    print("Configuration data has been written to config.json")

def connect_to_pool(pool_address, pool_port, timeout=30, retries=5):
    for attempt in range(retries):
        try:
            print(f"Attempting to connect to pool (Attempt {attempt + 1}/{retries})...")
            sock = socket.create_connection((pool_address, pool_port), timeout)
            print("Connected to pool!")
            return sock
        except socket.gaierror as e:
            print(f"Address-related error connecting to server: {e}")
        except socket.timeout as e:
            print(f"Connection timed out: {e}")
        except socket.error as e:
            print(f"Socket error: {e}")

        print(f"Retrying in 5 seconds...")
        time.sleep(5)
    
    raise Exception("Failed to connect to the pool after multiple attempts")

def send_message(sock, message):
    print(f"Sending message: {message}")
    sock.sendall((json.dumps(message) + '\n').encode('utf-8'))

def receive_messages(sock, timeout=30):
    buffer = b''
    sock.settimeout(timeout)
    while True:
        try:
            chunk = sock.recv(1024)
            if not chunk:
                break
            buffer += chunk
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                print(f"Received message: {line.decode('utf-8')}")
                yield json.loads(line.decode('utf-8'))
        except socket.timeout:
            print("Receive operation timed out. Retrying...")
            continue

def subscribe(sock):
    message = {
        "id": 1,
        "method": "mining.subscribe",
        "params": []
    }
    send_message(sock, message)
    for response in receive_messages(sock):
        if response['id'] == 1:
            print(f"Subscribe response: {response}")
            return response['result']

def authorize(sock, username, password):
    message = {
        "id": 2,
        "method": "mining.authorize",
        "params": [username, password]
    }
    send_message(sock, message)
    for response in receive_messages(sock):
        if response['id'] == 2:
            print(f"Authorize response: {response}")
            return response['result']

def calculate_difficulty(hash_result):
    hash_int = int.from_bytes(hash_result[::-1], byteorder='big')
    max_target = 0xffff * (2**208)
    difficulty = max_target / hash_int
    return difficulty

def mine_worker(job, target, extranonce1, extranonce2_size,
                nonce_start, nonce_end, duration, result_queue, stop_event, idx):
    pin_this_process_to_core(idx % os.cpu_count())
    job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, _ = job
    extranonce2 = struct.pack('<Q', 0)[:extranonce2_size]
    coinbase = (coinb1 + extranonce1 + extranonce2.hex() + coinb2).encode()
    coinbase_hash_bin = hashlib.sha256(hashlib.sha256(coinbase).digest()).digest()

    merkle_root = coinbase_hash_bin
    for branch in merkle_branch:
        merkle_root = hashlib.sha256(
            hashlib.sha256(merkle_root + bytes.fromhex(branch)).digest()
        ).digest()

    header = (version + prevhash + merkle_root[::-1].hex() + ntime + nbits).encode()
    target_bin = bytes.fromhex(target)[::-1]

    counter = 0
    t0 = time.time()
    end_ts = t0 + duration
    while time.time() < end_ts:
        for _ in range(10000):
            nonce_bin = struct.pack('<I', (nonce_start + counter) & 0xffffffff)
            hashlib.sha256(hashlib.sha256(header + nonce_bin).digest()).digest()
            counter += 1

    result_queue.put((idx, counter))


def mine(job, target, extranonce1, extranonce2_size, duration=60, num_processes=1):
    nonce_span = 2**32 // num_processes
    result_queue = multiprocessing.Queue()
    stop_event   = multiprocessing.Event()

    procs = []
    for i in range(num_processes):
        s = i * nonce_span
        e = (i + 1) * nonce_span
        p = multiprocessing.Process(
            target=mine_worker,
            args=(job, target, extranonce1, extranonce2_size,
                  s, e, duration, result_queue, stop_event, i)
        )
        p.start(); procs.append(p)

    time.sleep(duration)
    stop_event.set()
    for p in procs: p.join()

    per_process = [0]*num_processes
    while not result_queue.empty():
        idx, cnt = result_queue.get()
        per_process[idx] = cnt

    stats = {
        "num_processes": num_processes,
        "duration_sec": duration,
        "per_process": per_process,
        "total": sum(per_process),
    }
    fname = f"nonce_stats_{num_processes}proc.json"
    with open(fname, "w") as f:
        json.dump(stats, f, indent=4)
    print(f"[✔] Saved stats to {fname}")
    return stats


def submit_solution(sock, job_id, extranonce2, ntime, nonce):
    message = {
        "id": 4,
        "method": "mining.submit",
        "params": [username, job_id, extranonce2.hex(), ntime, struct.pack('<I', nonce).hex()]
    }
    send_message(sock, message)
    for response in receive_messages(sock):
        if response['id'] == 4:
            print("Submission response:", response)
            if response['result'] == False and response['error']['code'] == 23:
                print(f"Low difficulty share: {response['error']['message']}")
                return

if __name__ == "__main__":
    multiprocessing.freeze_support()

    with open(SAVE_PATH, "r") as f:
        saved = json.load(f)
    job, target = saved["job"], saved["target"]
    extranonce1, extranonce2_size = saved["extranonce1"], saved["extranonce2_size"]

    print("\n=== 1 Thread / 60s ===")
    mine(job, target, extranonce1, extranonce2_size,
         duration=60, num_processes=1)

    print("\n=== 16 Threads / 60s ===")
    mine(job, target, extranonce1, extranonce2_size,
         duration=60, num_processes=16)
