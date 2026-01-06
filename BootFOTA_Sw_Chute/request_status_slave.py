from slave_bootFOTA_main import run_FWD_master, request_status_slave
from master_bootFota_main import UdpConnection, reset_master

import socket
import time



if __name__ == "__main__":
    print("\n            -------------> REQUEST STATUS SLAVE <-----------\n")

    print("")
    HOST_INPUT = "192.168.1.200"
    print(HOST_INPUT)
    print("")
    PORT_INPUT = int(input("> Enter the PORT : " ))
    print("")
    ID_master = int(input("> Enter ID Master: " ) )
    print("")
  
    # HOST_INPUT = "192.168.1.200"
    # PORT_INPUT = 1111
    # ID_master = 1
    
    # Tạo socket UDP
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(1)  # Timeout cho việc nhận dữ liệu
    
    udp_params = UdpConnection(udp_socket, HOST_INPUT, PORT_INPUT)
    
    # Reset master before starting
    rlt = reset_master(ID_master=ID_master, UDP_SOCKET=udp_params)
    
    if not rlt:
        exit(1)
    
    # Wait a moment after reset 
    time.sleep(1.5)
        
    # Run mode Forward on MASTER
    run_FWD_master(ID_master=ID_master, UDP_SOCKET=udp_params)
    
    if not rlt:
        exit(1)
    
    while True:
        try:
            print("------------------- REQUEST STATUS SLAVE -------------------")
            ID_slave = int(input("> Enter ID Slave: " ) )
            if ID_slave == "":
                continue             
            request_status_slave(ID_master, ID_slave, UDP_SOCKET=udp_params) 
            
        except KeyboardInterrupt:
            time.sleep(0.5)
            reset_master(ID_master=ID_master, UDP_SOCKET=udp_params)
            print("\n->Exiting due to keyboard interrupt...\n")
            break