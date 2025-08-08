from master_bootFota_main import request_status_master, UdpConnection

import socket


if __name__ == "__main__":
    print("\n            -------------> REQUEST STATUS MASTER <-----------\n")

    print("")
    HOST_INPUT = "192.168.1." + input("> Enter the HOST : 192.168.1." )
    print("")
    PORT_INPUT = int(input("> Enter the PORT : " ))
    print("")
    ID_master = int(input("> Enter ID Master: " ) )
    print("")
    
    
    # Tạo socket UDP
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(1)  # Timeout cho việc nhận dữ liệu
    
    udp_params = UdpConnection(udp_socket, HOST_INPUT, PORT_INPUT)
    
    while True:
        # Start Booting by FOTA *****************************
        request_status_master(ID_master=ID_master, UDP_SOCKET=udp_params)
        
        try:
            ctn = input("\n> Do you want to continue? (y/n): ")
            if ctn.lower() != 'y':
                print("Exiting...")
                break
        except KeyboardInterrupt:
            print("\nExiting due to keyboard interrupt...")
            break