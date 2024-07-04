import socket
import sys
import os
import json
import time

ClientFolder = os.getcwd() + '/' + 'ClientFolder'
os.makedirs(ClientFolder, exist_ok=True)
os.chdir(ClientFolder)

def client(hostname, port):
    server_addr = (hostname, port)
    while True:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(server_addr)
            while True:
                user_input = input("ftp>> ")
                if user_input.lower() == 'quit':
                    client_string = {"Cmd": "QUIT"}
                    json_data = json.dumps(client_string)
                    client_socket.sendall(json_data.encode('utf-8'))
                    print("Exiting...")
                    client_socket.close()
                    return

                elif user_input.lower().startswith('ls'):
                    args = user_input.split()
                    if len(args) > 1:
                        print("The 'ls' command does not take any arguments.")
                        continue
                    client_string = {"Cmd": "List"}
                    json_data = json.dumps(client_string)
                    client_socket.sendall(json_data.encode('utf-8'))

                    data = client_socket.recv(1024)
                    if data:
                        server_response = json.loads(data.decode('utf-8'))
                        if server_response["StatusCode"] == 210:
                            print("Server response: Empty")
                        elif server_response["StatusCode"] == 150:
                            data_port = server_response["Port"]
                            data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            data_socket.connect((hostname, data_port))
                            print(f"Connected to data port {data_port}")
                            while True:
                                data = data_socket.recv(1024)
                                if not data:
                                    break
                                print(data.decode('utf-8'))
                            data_socket.close()
                            control_response = client_socket.recv(1024)
                            final_response = json.loads(control_response.decode('utf-8'))
                            if final_response["StatusCode"] == 226:
                                print("Server response: Directory send OK")

                elif user_input.lower().startswith('get '):
                    args = user_input.split()
                    if len(args) < 2:
                        print("The 'get' command requires a filename.")
                        continue
                    client_string = {"Cmd": "GET", "FileName": args[1]}
                    json_data = json.dumps(client_string)
                    client_socket.sendall(json_data.encode('utf-8'))
                    data = client_socket.recv(1024)
                    if data:
                        server_response = json.loads(data.decode('utf-8'))
                        if server_response["StatusCode"] == 550:
                            print("File doesn't exist")
                        elif server_response["StatusCode"] == 150:
                            data_port = server_response["Port"]
                            file_size = server_response["FileSize"]
                            print(f"Receiving file {args[1]} of size {file_size} bytes")
                            data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            data_socket.connect((hostname, data_port))
                            print(f"Connected to data port {data_port}")
                            start_time = time.time()
                            bytes_received = 0
                            with open(args[1], 'wb') as f:
                                while True:
                                    data = data_socket.recv(1024)
                                    if not data:
                                        break
                                    f.write(data)
                                    bytes_received += len(data)
                                    elapsed_time = time.time() - start_time
                                    transfer_rate = bytes_received / elapsed_time
                                    percentage = (bytes_received / file_size) * 100
                                    estimated_time = (file_size - bytes_received) / transfer_rate if transfer_rate > 0 else 0
                                    progress_bar = ('#' * int(percentage // 2)).ljust(50, '*')
                                    print(f"\rReceived {percentage:.2f}% [{progress_bar}] {bytes_received} of {file_size} bytes in {elapsed_time:.2f} seconds, transfer rate = {transfer_rate/1024:.2f} KB/s, estimated time = {estimated_time:.2f} seconds", end='')
                            
                                print(f'Received file and saved as {args[1]}')
                            data_socket.close()
                            control_response = client_socket.recv(1024)
                            final_response = json.loads(control_response.decode('utf-8'))
                            if final_response["StatusCode"] == 226:
                                print("Server response: Transfer complete")

                elif user_input.lower().startswith('put '):
                    args = user_input.split()
                    if len(args) < 2:
                        print("The 'put' command requires a filename.")
                        continue
                    filepath = os.path.join(ClientFolder, args[1])
                    if not os.path.exists(filepath):
                        print(f"File {args[1]} does not exist in the client folder.")
                        continue
                    file_size = os.path.getsize(filepath)
                    client_string = {"Cmd": "PUT", "FileName": args[1], "FileSize": file_size}
                    json_data = json.dumps(client_string)
                    client_socket.sendall(json_data.encode('utf-8'))

                    data = client_socket.recv(1024)
                    if data:
                        server_response = json.loads(data.decode('utf-8'))
                        if server_response["StatusCode"] == 434:
                            print("The client doesn't have the root access. File transfer aborted.")
                        elif server_response["StatusCode"] == 150:
                            data_port = server_response["Port"]
                            print(f"Sending file {args[1]} of size {file_size} bytes")
                            data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            data_socket.connect((hostname, data_port))
                            print(f"Connected to data port {data_port}")
                            start_time = time.time()
                            bytes_sent = 0
                            with open(args[1], 'rb') as f:
                                while (chunk := f.read(1024)):
                                    data_socket.sendall(chunk)
                                    bytes_sent += len(chunk)
                                    elapsed_time = time.time() - start_time
                                    transfer_rate = bytes_sent / elapsed_time
                                    percentage = (bytes_sent / file_size) * 100
                                    estimated_time = (file_size - bytes_sent) / transfer_rate if transfer_rate > 0 else 0
                                    progress_bar = ('#' * int(percentage // 2)).ljust(50, '*')
                                    print(f"\rSent {percentage:.2f}% [{progress_bar}] {bytes_sent} of {file_size} bytes in {elapsed_time:.2f} seconds, transfer rate = {transfer_rate/1024:.2f} KB/s, estimated time = {estimated_time:.2f} seconds", end='')
                            
                            print(f'Sent file {args[1]}')
                            data_socket.close()
                            control_response = client_socket.recv(1024)
                            final_response = json.loads(control_response.decode('utf-8'))
                            if final_response["StatusCode"] == 226:
                                print("Server response: Transfer complete")

                elif user_input.lower().startswith('mput '):
                    args = user_input.replace(',', ' ').split()
                    if len(args) < 3:
                        print("The 'mput' command requires multiple filenames separated by commas.")
                        continue
                    files = os.listdir(ClientFolder)
                    filenames = args[1:]
                    existed_files = []
                    for filename in filenames:
                        if filename in files:
                            existed_files.append(filename)
                        else:
                            print(f"File {filename} does not exist in the client folder.")
                    
                    if existed_files:
                        client_string = {"Cmd": "MPUT"}
                        for i in range(len(existed_files)):
                            file_size = os.path.getsize(existed_files[i])
                            client_string[f"FileName_{i+1}"] = existed_files[i]
                            client_string[f"FileSize_{i+1}"] = file_size  
                        json_data = json.dumps(client_string)
                        client_socket.sendall(json_data.encode('utf-8'))

                        data = client_socket.recv(1024)

                        if data:
                            server_response = json.loads(data.decode('utf-8'))

                            if server_response["StatusCode"] == 434:
                                print("The client doesn't have the root access. File transfer aborted.")
                            elif server_response["StatusCode"] == 150:
                                print(f"Connected to data port {data_port}")
                                for i in range(len(existed_files)):
                                    data_port = server_response["Port"]
                                    data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                    data_socket.connect((hostname, data_port))
                                    print(f"Sending file {existed_files[i]} of size {client_string[f'FileSize_{i+1}']} bytes")
                                    start_time = time.time()
                                    bytes_sent = 0
                                    with open(existed_files[i], 'rb') as f:
                                        while (chunk := f.read(1024)):
                                            data_socket.sendall(chunk)
                                            bytes_sent += len(chunk)
                                            elapsed_time = time.time() - start_time
                                            transfer_rate = bytes_sent / elapsed_time
                                            percentage = (bytes_sent / client_string[f'FileSize_{i+1}']) * 100
                                            estimated_time = (client_string[f'FileSize_{i+1}'] - bytes_sent) / transfer_rate if transfer_rate > 0 else 0
                                            progress_bar = ('#' * int(percentage // 2)).ljust(50, '*')
                                            print(f"\rSent {percentage:.2f}% [{progress_bar}] {bytes_sent} of {client_string[f'FileSize_{i+1}']} bytes in {elapsed_time:.2f} seconds, transfer rate = {transfer_rate/1024:.2f} KB/s, estimated time = {estimated_time:.2f} seconds", end='')
                                    
                                    data_socket.close()
                                    
                                    control_response = client_socket.recv(1024)
                                    final_response = json.loads(control_response.decode('utf-8'))
                                    if final_response["StatusCode"] == 226:
                                        print(f"Server response: Transfer complete for {existed_files[i]}")
                                data_socket.close()

                elif user_input.lower().startswith('delete'):
                    args = user_input.split()
                    if len(args) < 2:
                        print("The 'delete' command requires a filename.")
                        continue
                    client_string = {"Cmd": "DELE", "FileName": args[1]}
                    json_data = json.dumps(client_string)
                    client_socket.sendall(json_data.encode('utf-8'))

                    data = client_socket.recv(1024)
                    if data:
                        server_response = json.loads(data.decode('utf-8'))
                        if server_response["StatusCode"] == 434:
                            print("The client doesn't have the root access. File transfer aborted.")
                        elif server_response["StatusCode"] == 550:
                            print("File doesn't exist.")
                        elif server_response["StatusCode"] == 200:
                            print("Successfully deleted.")

                elif user_input.lower().startswith('ath'):
                    args = user_input.split()
                    if len(args) < 3 or len(args) > 3:
                        print("The 'ath' command requires a user and pass.")
                        continue
                    client_string = {"Cmd": "AUTH", "User": args[1], "Password": args[2]}
                    json_data = json.dumps(client_string)
                    client_socket.sendall(json_data.encode('utf-8'))
                    data = client_socket.recv(1024)
                    if data:
                        server_response = json.loads(data.decode('utf-8'))
                        if server_response["StatusCode"] == 430:
                            print("Failure in granting root accessibility")
                        elif server_response["StatusCode"] == 230:
                            print(" Successfully logged in. Proceed")
                else:
                    print(f"Unknown command: {user_input}")
        except (ConnectionResetError, BrokenPipeError):
            print("Connection lost. Reconnecting...")
            client_socket.close()

if __name__ == "__main__":
    hostname = '127.0.0.1'  
    port = 20022
    client(hostname, port)
