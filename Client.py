import socket
import threading
import time
import sys
import struct


MAGIC_COOKIE = 0xabcddcba
MSG_OFFER = 0x2
MSG_REQUEST = 0x3
MSG_PAYLOAD = 0x4


LISTEN_PORT = 13117
UDP_BUFFER_SIZE = 1024 #udp is smaller the tcp to avoid fragmentation and packet loss when in tcp the protocol change the buffer size dynamically
TCP_BUFFER_SIZE = 4096




class Client:
    def __init__(self):
        self.client_name = "Nirvana"
        self.running = True
        #craete udp socket to listen to offers

        self.udp_sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.udp_sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.udp_sock.bind(("",LISTEN_PORT))
        self.status = "STARTUP"


    def run(self):
        while self.running:
            self.start_dialog(self)
            print("Client started, listening for offer request...")
            self.wait_for_offer(self)





    
    def start_dialog(self):
        try:
            #ask the user for file size , number of tcp connections and number of udp connections
            print(f"Welcome to {self.client_name} please enter the file size you desire in Bytes")
            self.file_size = int(sys.stdin.readline().strip())

            print("please enter the number of TCP connections")
            self.num_tcp_connections = int(sys.stdin.readline().strip())

            print("please enter the number of udp connections")
            self.num_udp_connections = int(sys.stdin.readline().strip())

            
        except:
            print("Invalid input, reset to default (1GB, 1TCP, 1UDP)")
            self.file_size =10**9
            self.num_tcp_connections = 1
            self.num_udp_connections = 1

        finally:
            self.status = "WAIT_FOR_OFFER"


    def wait_for_offer(self):
        while self.status == "WAIT_FOR_OFFER":
            data, addr = self.udp_sock.recvfrom(UDP_BUFFER_SIZE)
            if self._parse_offer(data):
                print(f"Received offer from {addr[0]}, UDP port: {self.server_udp_port}, TCP port: {self.server_tcp_port}")
                

                self.server_addr = addr[0]
                self.status = "SPEED_TEST"
                return




    def _parse_offer(self, data):
        try:
            if len(data) < 9:
                return False
            # parse first 4 bytes as magic cookie, 1 for type and more 4 for the ports.
            unpacked = struct.unpack('!IBHH', data[:9])
            cookie, msg_type, udp_port, tcp_port = unpacked
            if cookie != MAGIC_COOKIE or msg_type != MSG_OFFER:
                return False
            
            self.server_udp_port = udp_port
            self.server_tcp_port = tcp_port
            return True
        except:
            return False
        