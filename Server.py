import socket
import threading
import time
import struct


#Constants
MAGIC_COOKIE = 0xabcddcba
MSG_OFFER = 0x2
MSG_REQUEST = 0x3
MSG_PAYLOAD = 0x4

BROADCAST_PORT = 13117
OFFER_INTERVAL = 1.0
UDP_BUFFER_SIZE = 1024 #udp is smaller the tcp to avoid fragmentation and packet loss when in tcp the protocol change the buffer size dynamically
TCP_BUFFER_SIZE = 4096

class Server:
    def __init__(self):
        self.server_name = "Oasis"


        #create tcp socket to listen to incoming messages coming in tcp
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(('',0)) #bind to any available port
        self.tcp_socket.listen(5)


        #store the tcp port so we can add it to the broadcast
        self.tcp_port = self.tcp_socket.getsockname()[1]


        #create UDP socket to listen to incaming udp requests
        self.udp_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.udp_socket.bind(('', 0))
        self.udp_port = self.udp_socket.getsockname()[1]


        print(f"[{self.server_name}] server started, listening on TCP {self.tcp_port}, UDP {self.udp_port}")

        self.running = True




    def _division_of_labor(self):
        threading.Thread(target= self._broadcast_offers).start()
        threading.Thread(target= self._accept_tcp_connections).start()
        threading.Thread(target=self._accept_udp_request).start()

        while self.running:
            time.sleep(1)





    def _broadcast_offers(self):
        """Broadcast offer packets once every second"""
        broadcast_sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        broadcast_sock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
        while self.running:
            #Build the offer packet:
            packet = struct.pack('!IBHH', MAGIC_COOKIE, MSG_OFFER, self.udp_port,self.tcp_port)
            broadcast_sock.sendto(packet, ('<broadcast>', BROADCAST_PORT))
            time.sleep(OFFER_INTERVAL)
        

    def _accept_tcp_connections(self):
        """accept tcp connection and start a thread for each one"""
        while self.running:
            client_socket, addr = self.tcp_socket.accept() # one thread handle the accept socket so there no will be stuck, this methos return (client ip, client port)
            print(f"[{self.server_name}] TCP connection from {addr}")
            threading.Thread(target= self._handle_tcp_client, args= (client_socket,)).start()##the thread to handle specific client



    def _handle_tcp_client(self, client_socket): ## the client socket is a socket that the os kernel create
        """Handles a single TCP client"""
        try:
            data = b""
            while b'\n' not in data:
                chunk = client_socket.recv(TCP_BUFFER_SIZE) 
                if not chunk:
                    break
                data +=chunk

            line = data.decode().strip()
            requested_size = int(line)
            print(f"[{self.server_name}] Client requested {requested_size} bytes (TCP)" )



            bytes_sent = 0
            chunk_size = 4096
            while bytes_sent < requested_size:
                remaining = requested_size - bytes_sent
                to_send = min(chunk_size, remaining)
                client_socket.send(b'X' * to_send)
                bytes_sent += to_send
            
        except Exception as e:
            print(f"[{self.server_name}] TCP client handler error: {e}")

        finally:
            client_socket.close()


    def _accept_udp_request(self):
        data, addr = self.udp_socket.recvfrom(UDP_BUFFER_SIZE)
        threading.Thread(target = self._handle_udp_client, args=(data, addr)
                         ).start()


    def _handle_udp_client(self,data,addr):
        try:
            rcv_data = struct.unpack('!IBQ',data)
            msg_cookie, msg_type, file_size = rcv_data


            if((msg_cookie != MAGIC_COOKIE) or (msg_type!=MSG_REQUEST)):
                print(f"[{self.server_name}] Invalid UDP request check the magic cookie or type")
                return
            print(f"({self.server_name}) got UDP request from {addr} of size{file_size}")

            total_seg_to_send = (file_size + UDP_BUFFER_SIZE-1) // UDP_BUFFER_SIZE

            for i  in range(total_seg_to_send):
                curr_seg = i+1
                seg_size = UDP_BUFFER_SIZE
                if i == total_seg_to_send-1:#if we are in the final segment send only what remind not all the buffer
                    seg_size = file_size - (i*seg_size)
            
                header = struct.pack('!IBQQ',
                                    MAGIC_COOKIE,
                                    MSG_PAYLOAD,
                                    total_seg_to_send,
                                    curr_seg)
                
                packet = header + (b'Z' * seg_size)
                self.udp_socket.sendto(packet,addr)


        except Exception as e:
            print(f"got {e} in UDP handeling ")







if __name__ == "__main__":
    server = Server()
    server._division_of_labor()
