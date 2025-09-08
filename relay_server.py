import socket
import threading
import os
import pickle
import struct

HOST = '192.168.1.131'
PORT = int(os.environ.get('PORT', 65432)) 

# Dictionary to store connected sessions
sessions = {}
sessions_lock = threading.Lock()

def handle_session(conn, addr):
    print(f"New connection from {addr}")
    try:
        # Receive ID from the client
        conn.settimeout(10)
        # Assuming the ID is a 6-digit number, sent as bytes
        client_id_bytes = conn.recv(6)
        if not client_id_bytes:
            raise Exception("No ID received")
        client_id = client_id_bytes.decode('utf-8')
        print(f"Client {addr} identified as ID: {client_id}")

        with sessions_lock:
            if client_id in sessions:
                # If a matching session exists, start relaying data
                other_conn = sessions.pop(client_id)
                print(f"Matching session found for {client_id}. Starting relay.")
                threading.Thread(target=relay_data, args=(conn, other_conn)).start()
                threading.Thread(target=relay_data, args=(other_conn, conn)).start()
            else:
                # If not, store this session and wait for a partner
                sessions[client_id] = conn
                print(f"Session {client_id} stored. Waiting for a partner.")
    except Exception as e:
        print(f"Error handling connection: {e}")
        conn.close()

def relay_data(from_conn, to_conn):
    try:
        while True:
            # Read the size of the next message
            raw_size = from_conn.recv(struct.calcsize("L"))
            if not raw_size:
                break
            size = struct.unpack("L", raw_size)[0]

            # Read the message data
            data = bytearray()
            while len(data) < size:
                packet = from_conn.recv(size - len(data))
                if not packet:
                    break
                data.extend(packet)
            
            # Forward the data
            to_conn.sendall(raw_size + data)
    except Exception as e:
        print(f"Relay error: {e}")
    finally:
        from_conn.close()
        to_conn.close()

def start_relay_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Relay server listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_session, args=(conn, addr)).start()

if __name__ == "__main__":

    start_relay_server()
