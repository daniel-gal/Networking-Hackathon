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
UDP_BUFFER_SIZE = 4096 #udp is smaller the tcp to avoid fragmentation and packet loss when in tcp the protocol change the buffer size dynamically
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
            if self.status == "STARTUP":
                self.start_dialog()
                print("Client started, listening for offer request...")
            ##elif self.status == "WAIT_FOR_OFFER":
            self.wait_for_offer()
            ##elif self.status == "SPEED_TEST":
            self._speed_test()

            print(f"[{self.client_name}] All transfers complete, listening to offer requests")




    
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
        

    def _speed_test(self):
        self.times =[]
        self.threads = []

        ##handle the tcp requests
        for i in range(self.num_tcp_connections):
            t = threading.Thread(target = self._tcp_handle, args=(i+1,))
            t.start()
            self.threads.append(t)

        ##handle the udp requested
        for i in range(self.num_udp_connections):
            t = threading.Thread(target = self.udp_handle,args = (i+1,))
            t.start()
            self.threads.append(t)

        #for the main thread to wait for all the rest
        for t in self.threads:
            t.join()

    def _tcp_handle(self,index):
        start_time = time.time()
        bytes_rec = 0
        
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as tcp_sock:
                tcp_sock.connect((self.server_addr,self.server_tcp_port))
                #send request 
                tcp_sock.sendall(str(self.file_size).encode()+ b'\n')

                ##recieve data
                while bytes_rec < self.file_size:
                    chunck = tcp_sock.recv(TCP_BUFFER_SIZE)
                    if not chunck:
                        break
                    bytes_rec += len(chunck)
        except Exception as e:
            print(f"tcp {index} error: {e}")
        
        end_time = time.time()
        duration = end_time-start_time
        bps_speed = (bytes_rec * 8) /duration if duration>0 else 0

        print(f"[{self.client_name}] TCP transfer #{index} finished, "
              f"total time: {duration:.2f} seconds, "
              f"speed: {bps_speed:.2f} bits/sec")

        self.times.append(("TCP", index, duration, bps_speed))


    def udp_handle(self,index):
        start_time = time.time()
        Bytes_rec = 0
        Packet_rec = 0
        total_seg_main = 1

        request_packet = struct.pack('!IBQ',MAGIC_COOKIE,MSG_REQUEST,self.file_size)

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock1:
            udp_sock1.settimeout(1.0)
            try:

                #send request
                udp_sock1.sendto(request_packet,(self.server_addr,self.server_udp_port))

                last_rec_time = time.time()

                while True:
                    try:
                        data, addr = udp_sock1.recvfrom(UDP_BUFFER_SIZE)
                        current_time = time.time()
                        last_rec_time = current_time

                        if len(data)<21:
                            continue


                        header = data[:21]
                        try:
                            unpack = struct.unpack('!IBQQ', header)
                            cookie, msg_type, total_seg, current = unpack
                            total_seg_main = total_seg
                            if cookie != MAGIC_COOKIE or msg_type != MSG_PAYLOAD:
                                # invalid packet, ignore
                                continue
                        except:
                            continue

                        payload = data[21:]
                        Bytes_rec += len(payload)
                        Packet_rec += 1

                    except socket.timeout:
                        break

            except Exception as e:
                print(f"[{self.client_name}] UDP {index} error: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        speed_bps = (Bytes_rec * 8) / duration if duration > 0 else 0
        recive_pre = (Packet_rec/total_seg_main) * 100


        print(f"[{self.client_name}] UDP transfer #{index} finished, "
              f"total time: {duration:.2f} seconds, "
              f"speed: {speed_bps:.2f} bits/sec, "
              f"packets received successfully: {recive_pre:.2f}%")
        
        self.times.append(("UDP", index, duration, speed_bps, recive_pre))



if __name__ == "__main__":
    client = Client()
    client.run()

