import socket
import json
import os
import random
import subprocess
import threading
import time

ServerFolder = os.getcwd() + '/' + 'ServerFolder'
os.makedirs(ServerFolder, exist_ok=True)
os.chdir(ServerFolder)

def check_auth(user, password):
    with open('../users.txt', 'r') as f:
        users = f.readlines()
    for line in users:
        stored_user, stored_pass = line.strip().split(',')
        if stored_user == user and stored_pass == password:
            return True
    return False

def handle_client_connection(client_socket):
    authenticated = False
    bandwidth_limit = 1024 * 5000
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            client_string = json.loads(data.decode('utf-8'))
            
            if client_string["Cmd"] == "AUTH":
                user = client_string["User"]
                password = client_string["Password"]
                if check_auth(user, password):
                    authenticated = True
                    server_response = {
                        "StatusCode": 230,
                        "Description": "Successfully logged in. Proceed"
                    }
                else:
                    server_response = {
                        "StatusCode": 430,
                        "Description": "Failure in granting root accessibility"
                    }
                client_socket.sendall(json.dumps(server_response).encode('utf-8'))

            elif client_string["Cmd"] == "QUIT":
                server_response = {
                    "StatusCode": 200,
                    "Description": "Connection closed"
                }
                client_socket.sendall(json.dumps(server_response).encode('utf-8'))
                break
            
            elif client_string["Cmd"] == "List":
                files = os.listdir(ServerFolder)
                if not files:
                    server_response = {
                        "StatusCode": 210,
                        "Description": "Empty"
                    }
                else:
                    data_port = random.randint(10025, 49151)
                    server_response = {
                        "StatusCode": 150,
                        "Description": "Port Command Successful",
                        "Port": data_port
                    }
                    client_socket.sendall(json.dumps(server_response).encode('utf-8'))
                    
                    data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    data_socket.bind(('127.0.0.1', data_port))
                    data_socket.listen(1)
                    print(f"Data socket listening on port {data_port}")
                    conn, addr = data_socket.accept()

                    proc = subprocess.Popen(['ls', '-l', ServerFolder], stdout=subprocess.PIPE)
                    while True:
                        output = proc.stdout.read(1024)
                        if not output:
                            break
                        conn.sendall(output)
                    conn.close()
                    data_socket.close()
                    server_response = {
                        "StatusCode": 226,
                        "Description": "Directory send OK"
                    }
                client_socket.sendall(json.dumps(server_response).encode('utf-8'))
            
            elif client_string["Cmd"] == "GET":
                files = os.listdir(ServerFolder)
                if client_string["FileName"] not in files:
                    server_response = {
                        "StatusCode": 550,
                        "Description": "File doesn't exist"
                    }
                    client_socket.sendall(json.dumps(server_response).encode('utf-8'))
                else:
                    data_port = random.randint(10025, 49151)
                    file_size = os.path.getsize(client_string["FileName"])
                    server_response = {
                        "StatusCode": 150,
                        "Description": "Ok to Send Data",
                        "Port": data_port,
                        "FileSize": file_size
                    }
                    client_socket.sendall(json.dumps(server_response).encode('utf-8'))
                    print(f"Sending file {client_string['FileName']} of size {file_size} bytes")
                    data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    data_socket.bind(('0.0.0.0', data_port))
                    data_socket.listen(1)
                    print(f"Data socket listening on port {data_port}")
                    conn, addr = data_socket.accept()
                    print(f"Data connection from {addr}")
                    start_time = time.time()
                    bytes_sent = 0
                    with open(client_string["FileName"], 'rb') as f:
                        while (chunk := f.read(1024)):
                            conn.sendall(chunk)
                            bytes_sent += len(chunk)
                            time.sleep(len(chunk) / bandwidth_limit)
                            elapsed_time = time.time() - start_time
                            transfer_rate = bytes_sent / elapsed_time
                            percentage = (bytes_sent / file_size) * 100
                            estimated_time = (file_size - bytes_sent) / transfer_rate if transfer_rate > 0 else 0
                            progress_bar = ('#' * int(percentage // 2)).ljust(50, '*')
                            print(f"\rSent {percentage:.2f}% [{progress_bar}] {bytes_sent} of {file_size} bytes in {elapsed_time:.2f} seconds, transfer rate = {transfer_rate/1024:.2f} KB/s, estimated time = {estimated_time:.2f} seconds", end='')
                    print(f'Sent file {client_string["FileName"]}')
                    conn.close()
                    data_socket.close()
                    server_response = {
                        "StatusCode": 226,
                        "Description": "Transfer Complete"
                    }
                    client_socket.sendall(json.dumps(server_response).encode('utf-8'))
            
            elif client_string["Cmd"] == "PUT":
                if not authenticated:
                    server_response = {
                        "StatusCode": 434,
                        "Description": "The client doesn't have the root access. File transfer aborted."
                    }
                    client_socket.sendall(json.dumps(server_response).encode('utf-8'))
                else:
                    data_port = random.randint(10025, 49151)
                    server_response = {
                        "StatusCode": 150,
                        "Description": "Ok to Send Data",
                        "Port": data_port
                    }
                    client_socket.sendall(json.dumps(server_response).encode('utf-8'))
                    print(f"Receiving file {client_string['FileName']} of size {client_string['FileSize']} bytes")
                    
                    data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    data_socket.bind(('0.0.0.0', data_port))
                    data_socket.listen(10)
                    print(f"Data socket listening on port {data_port}")
                    conn, addr = data_socket.accept()
                    
                    start_time = time.time()
                    bytes_received = 0
                    with open(client_string["FileName"], 'wb') as f:
                        while True:
                            data = conn.recv(1024)
                            if not data:
                                break
                            f.write(data)
                            bytes_received += len(data)
                            time.sleep(len(data) / bandwidth_limit)
                            elapsed_time = time.time() - start_time
                            transfer_rate = bytes_received / elapsed_time
                            percentage = (bytes_received / client_string["FileSize"]) * 100
                            estimated_time = (client_string["FileSize"] - bytes_received) / transfer_rate if transfer_rate > 0 else 0
                            progress_bar = ('#' * int(percentage // 2)).ljust(50, '*')
                            print(f"\rReceived {percentage:.2f}% [{progress_bar}] {bytes_received} of {client_string['FileSize']} bytes in {elapsed_time:.2f} seconds, transfer rate = {transfer_rate/1024:.2f} KB/s, estimated time = {estimated_time:.2f} seconds", end='')
                   
                    print(f'Received file and saved as {client_string["FileName"]}')
                    conn.close()
                    data_socket.close()
                    server_response = {
                        "StatusCode": 226,
                        "Description": "Transfer Complete"
                    }
                    client_socket.sendall(json.dumps(server_response).encode('utf-8'))

            
            elif client_string["Cmd"] == "MPUT":
                if not authenticated:
                    server_response = {
                        "StatusCode": 434,
                        "Description": "The client doesn't have the root access. File transfer aborted."
                    }
                    client_socket.sendall(json.dumps(server_response).encode('utf-8'))
                else:
                    data_port = random.randint(10025, 49151)
                    server_response = {
                            "StatusCode": 150,
                            "Description": "Ok to Send Data",
                            "Port": data_port
                        }
                    client_socket.sendall(json.dumps(server_response).encode('utf-8'))

                    print(f"Data socket listening on port {data_port}")

                    for i in range(1, int(len(client_string.keys())/2) + 1):
                        data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        data_socket.bind(('0.0.0.0', data_port))
                        data_socket.listen(10)
                        conn, addr = data_socket.accept() 
                        print(f"Receiving file {client_string[f'FileName_{i}']} of size {client_string[f'FileSize_{i}']} bytes")                      
                        start_time = time.time()
                        bytes_received = 0
                        with open(client_string[f"FileName_{i}"], 'wb') as f:
                            while True:
                                data = conn.recv(1024)
                                if not data:
                                    break
                                f.write(data)
                                bytes_received += len(data)
                                time.sleep(len(data) / bandwidth_limit)
                                elapsed_time = time.time() - start_time
                                transfer_rate = bytes_received / elapsed_time
                                percentage = (bytes_received / client_string[f"FileSize_{i}"]) * 100
                                estimated_time = (client_string[f"FileSize_{i}"] - bytes_received) / transfer_rate if transfer_rate > 0 else 0
                                progress_bar = ('#' * int(percentage // 2)).ljust(50, '*')
                                print(f"\rReceived {percentage:.2f}% [{progress_bar}] {bytes_received} of {client_string[f'FileSize_{i}']} bytes in {elapsed_time:.2f} seconds, transfer rate = {transfer_rate/1024:.2f} KB/s, estimated time = {estimated_time:.2f} seconds", end='')
                    
                        conn.close()
                        data_socket.close()
                        print(f'Received file and saved as {client_string[f"FileName_{i}"]}')
                        
                        
                        server_response = {
                            "FileName": client_string[f"FileName_{i}"],
                            "StatusCode": 226,
                            "Description": "Transfer Complete"
                        }
                        client_socket.sendall(json.dumps(server_response).encode('utf-8'))
                    # conn.close()
                    
    
            elif client_string["Cmd"] == "DELE":
                if not authenticated:
                    server_response = {
                        "StatusCode": 434,
                        "Description": "The client doesn't have the root access. File transfer aborted."
                    }
                else:
                    files = os.listdir(ServerFolder)
                    if client_string["FileName"] not in files:
                        server_response = {
                            "StatusCode": 550,
                            "Description": "File doesn't exist"
                        }
                    else:
                        os.remove(client_string["FileName"])
                        server_response = {
                            "StatusCode": 200,
                            "Description": "Successfully Deleted",
                        }                      
                client_socket.sendall(json.dumps(server_response).encode('utf-8'))
    
    except (ConnectionResetError, BrokenPipeError):
        print("Client disconnected.")
    finally:
        client_socket.close()

def server_program():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('127.0.0.1', 20022))
    server_socket.listen(5)  # Allow multiple connections
    print("Server is listening...")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        client_handler = threading.Thread(target=handle_client_connection, args=(client_socket,))
        client_handler.start()

if __name__ == '__main__':
    server_program()
