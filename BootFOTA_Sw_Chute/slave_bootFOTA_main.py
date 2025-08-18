from master_bootFota_main import UdpConnection, reset_master,crc8, sendto_master, build_start_mess_bootFota_process \
                                                            , build_runApp_fw_mess
                                                                         

import socket
import os
import time

from datetime import datetime
from analysis_hex import analysis_hex


class UdpConnection:
    def __init__(self, socket, host, port):
        self.socket = socket
        self.host = host
        self.port = port

CMD_STATUS			=		0xA0
CMD_RUN_BOOTLOADER	=       0xA1
CMD_START_FLASHING	=       0xA2
CMD_FLASHING		=		0xA3
CMD_VERIFY_DATA		=	    0xA4
CMD_RUN_APP			=		0xA5

BOOTFOTA_FW_RUNNING     =   0x11
APPLICATION_FW_RUNNING     =   0x22

MASTER_CHUTE_CIRCUIT = 0x01
SLAVE_CHUTE_CIRCUIT = 0x02

SUCCESS = 0x59
FAIL = 0x4E

# ======================================================================================================
def build_forward_mode(ID_master:int)->bytearray:
    data_fwd = bytearray(4)
    data_fwd[0] = 0xD0 | (ID_master&0x0F)
    data_fwd[1] = 4
    data_fwd[2] = 0x0D
    data_fwd[3] = crc8(data_fwd, 4)

    return data_fwd

def receive_runFWD_mode_master(UDP_SOCKET, ID_master):
    try:
        data_read, _ = UDP_SOCKET.socket.recvfrom(256) 
        
        if len(data_read) > 2:
            cmd = data_read[0] & 0xF0
            id_m = data_read[0] & 0x0F
        
        if crc8(data_read, len(data_read)) == data_read[-1] \
                                    and id_m == ID_master   \
                                    and cmd == 0xD0          \
                                    and data_read[0] != 0x00:
            print("-> [Received] - ", " ".join(f"{b:02X}" for b in data_read))
            return True
        else:
            return False
    except socket.timeout:
        print("-> [Timeout] - Timeout Receive Response !")
        return False
    
# ======================================================================================================
def build_request_status_slave(ID_master:int, ID_slave:int)->bytearray:
    data_slave = bytearray(4)
    
    data_slave[0] = ID_slave   # ID slave
    data_slave[1] = 0x04       # Command to request status
    data_slave[2] = CMD_STATUS       # get status cmd
    data_slave[3] = crc8(data_slave, 4)
    
    data_master = bytearray(7)
    
    data_master[0] = 0xE0 | (ID_master&0x0F)
    data_master[1] = 7
    
    for i in range(0, 4):
        data_master[i+2] = data_slave[i]
        
    data_master[6] = crc8(data_master, 7)

    return data_master

def receive_status_slave(UDP_SOCKET, ID_master, ID_slave):
    try:
        data_read, _ = UDP_SOCKET.socket.recvfrom(256) 
        
        if len(data_read) > 3:
            cmd_m = data_read[0] & 0xF0
            id_m = data_read[0] & 0x0F
            
            id_sl = data_read[2]
            cmd_sl = data_read[4]
        
            if crc8(data_read, len(data_read)) == data_read[-1] \
                    and id_m == ID_master   \
                    and cmd_m == 0xE0          \
                    and data_read[0] != 0x00    \
                    and id_sl == ID_slave :
                        
                print("-> [Received] - ", " ".join(f"{b:02X}" for b in data_read))
                current_mode = data_read[5]
                ver_app = data_read[6]
                day = data_read[7]
                mon = data_read[8]
                year = (data_read[9] << 8) | data_read[10]
                stack_ptr = (data_read[11]<<24) | (data_read[12]<<16) | (data_read[13]<<8) | data_read[14]
                type_circuit = data_read[15]
                
                if current_mode == BOOTFOTA_FW_RUNNING:
                    mode = "Running Boot FOTA Program"
                elif current_mode == APPLICATION_FW_RUNNING:
                    mode = "Running Application Program"
                else:
                    mode = "not found"
                
                type_ = "not found"    
                if type_circuit == MASTER_CHUTE_CIRCUIT:
                    type_ = "Master Chute"     
                elif type_circuit == SLAVE_CHUTE_CIRCUIT:
                    type_ = "Slave Chute"
                    
                print(f"-> [Information]  - Type of circuit: {type_} - ")
                print(f"                  - Identify: {id_m}  ")
                print(f"                  - Current Mode: {mode}  ")
                print(f"                  - Version: {round(ver_app/10,1)} ")
                print(f"                  - Updated on: {day}/{mon}/{year}  ")
                print(f"                  - StackPointer Address: {hex(stack_ptr)}")
                return current_mode, True
            else:
                print("-> [Error] - Unexpected Response !")
                print("-> [Received] - ", " ".join(f"{b:02X}" for b in data_read))
                return False, False
        else:
            print("-> [Error] - Response too short !")
            return False, False
    except socket.timeout:
        print("-> [Timeout] - Timeout Receive Response !")
        return False, False

# ======================================================================================================
def build_start_mess_bootFota_process_slave(ID_master: int, Identify: int, addr_start, addr_end)->bytearray:
    
    mess_slave = build_start_mess_bootFota_process(Identify, addr_start, addr_end)
    
    mess_sent = bytearray(15)
    
    mess_sent[0] = 0xE0 | (ID_master & 0x0F)  # ID Master
    mess_sent[1] = 15                        # Length of message
    
    # Copy mess_slave vào mess_sent từ vị trí 2
    for i in range(len(mess_slave)):
        mess_sent[i+2] = mess_slave[i]
    
    mess_sent[14] = crc8(mess_sent, 15)  # CRC
 
    return mess_sent

def receive_startBootFota_response_slave(UDP_SOCKET, ID_master, SQ_slave):
    try:
        data_read, _ = UDP_SOCKET.socket.recvfrom(256)
        
        if len(data_read) == 9:
            id_m = data_read[0] & 0x0F
            id_s = data_read[2]   
            cmd = data_read[4]

            # Kiểm tra CRC và byte phản hồi hợp lệ
            if crc8(data_read, len(data_read)) == data_read[-1] \
                                        and cmd == CMD_START_FLASHING \
                                        and id_m == ID_master \
                                        and id_s == SQ_slave:            
                print("-> [Received] - ", " ".join(f"{b:02X}" for b in data_read))
                rlt = data_read[5]                  # result
                num_page = data_read[6]
                
                if rlt == SUCCESS:
                    print(f"-> [Result] - Erased {num_page} pages on Slave {id_s}, Master {id_m}. Start Flashing Success!")
                    return True
                else:
                    print("-> [Result] - Erased Fail. Start Flashing Fail !")
            else:
                print("-> [Error] - Unexpected Response!")
                return False
        else:
            print("-> [Error] - Response too short !")
            return False

    except socket.timeout:
        print("-> [Timeout] - Receive Response Timeout !")
        return False

# ======================================================================================================
def build_runApp_fw_mess_slave(ID_master, Identify, stack_pointer, version, _date_now, type_circuit)->bytearray:

    mess_slave = build_runApp_fw_mess(Identify, stack_pointer, version, _date_now, type_circuit)
    
    mess_sent = bytearray(17)
    
    mess_sent[0] = 0xE0 | (ID_master & 0x0F)  # ID Master
    mess_sent[1] = 17                        # Length of message
    
    # Copy mess_slave vào mess_sent từ vị trí 2
    for i in range(len(mess_slave)):
        mess_sent[i+2] = mess_slave[i]
        
    mess_sent[16] = crc8(mess_sent, 17)  # CRC
    
    return mess_sent

def receive_runApp_fw_mess_slave(UDP_SOCKET, ID_master, SQ_slave):
    try:
        data_read, _ = UDP_SOCKET.socket.recvfrom(256)
        
        if len(data_read) == 8:
            id_m = data_read[0] & 0x0F
            id_s = data_read[2]   
            cmd = data_read[4]

            if crc8(data_read, len(data_read)) == data_read[-1] \
                                        and id_s == SQ_slave \
                                        and id_m == ID_master \
                                        and cmd == CMD_RUN_APP:
                print("-> [Received] - ", " ".join(f"{b:02X}" for b in data_read))
                rlt = data_read[5]

                if rlt == SUCCESS:
                    # print(f"-> Send Command Run Application Fw on Master {ID_master_input} SUCCESS !")
                    return True
                else:
                    # print(f"-> Send Command Run Application Fw on Master {ID_master_input} FAILURE !")
                    return False
            else:
                print("-> [Error] - Unexpected response!")
                return False
        else:
            print("-> [Error] - Response too short !")
            return False

    except socket.timeout:
        print("-> Timeout Response !")

# ======================================================================================================
def build_mess_run_bootFOTA_slave(ID_master: int, ID_slave: int) -> bytearray:
    
    data_slave = bytearray(4)
    
    data_slave[0] = ID_slave                    # ID slave
    data_slave[1] = 0x04                     # Command to request status
    data_slave[2] = CMD_RUN_BOOTLOADER       # get status cmd
    data_slave[3] = crc8(data_slave, 4)
    
    data_master = bytearray(7)
    
    data_master[0] = 0xE0 | (ID_master&0x0F)
    data_master[1] = 7
    
    for i in range(0, 4):
        data_master[i+2] = data_slave[i]
        
    data_master[6] = crc8(data_master, 7)

    return data_master

def receive_runFOTA_slave_response(UDP_SOCKET, ID_master, SQ_slave):
    try:
        data_read, _ = UDP_SOCKET.socket.recvfrom(256)
        
        if len(data_read) == 8:
            id_m = data_read[0] & 0x0F
            id_s = data_read[2]   
            cmd = data_read[4]
        
            # Kiểm tra CRC và byte phản hồi hợp lệ
            if crc8(data_read, len(data_read)) == data_read[-1] \
                                        and cmd == CMD_RUN_BOOTLOADER         \
                                        and id_m == ID_master   \
                                        and id_s == SQ_slave:
                
                print("-> [Received] - ", " ".join(f"{b:02X}" for b in data_read))
                
                rlt = data_read[5]                  # result
                
                if rlt == SUCCESS:
                    return True
                else:
                    return False
            else:
                print("-> [Error] - Unexpected Response!")
                return False
        else:
            print("-> [Error] - Response too short !")
            return False

    except socket.timeout:
        print("-> [Timeout] - Receive Response Timeout !")
        return False

   
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
def run_FWD_master(ID_master, UDP_SOCKET={}, retry=100):
    # 
    print(f"\n>>>>>>>>>>>>>> RUN FORWADER MODE MASTER {ID_master}, "
            f"HOST '{UDP_SOCKET.host}', PORT '{UDP_SOCKET.port}'\n")
    mess_sent = build_forward_mode(ID_master)
    while retry>0:
        sendto_master(mess_sent, UDP_SOCKET)
        print("-> [Sent] - ", " ".join(f"{b:02X}" for b in mess_sent))
        
        result = receive_runFWD_mode_master(UDP_SOCKET, ID_master)
        
        if result:
            print(f"-> [Result] - Run forwarder mode on MASTER {ID_master} Success !")
            return True
        else:
            retry -= 1
            
        time.sleep(0.5)
        
    print(f"-> [Result] - Run forwarder mode on MASTER {ID_master} Fail !")
    return False

# ======================================================================================================
def request_status_slave(ID_master, ID_slave, UDP_SOCKET={}, retry=100):
    # 
    print(f"\n>>>>>>>>>>>>>> REQUEST STATUS SLAVE {ID_slave}, MASTER {ID_master}, "
            f"HOST '{UDP_SOCKET.host}', PORT '{UDP_SOCKET.port}'\n")
    mess_sent = build_request_status_slave(ID_master, ID_slave)
    while retry>0:
        sendto_master(mess_sent, UDP_SOCKET)
        print("-> [Sent] - ", " ".join(f"{b:02X}" for b in mess_sent))
        
        current_mode, result = receive_status_slave(UDP_SOCKET, ID_master, ID_slave)
        
        if result:
            return current_mode
        else:
            retry -= 1
            
        time.sleep(0.5)
        
    print(f"-> [Result] - Request Status SLAVE {ID_slave}, MASTER {ID_master} Fail !")
    return False

# ======================================================================================================
def start_bootFota_process(ID_master, SQ_slave, UDP_SOCKET={}, addr_start=0, addr_end=0, retry=100):
    # Send start boot command to Slave ------------------------------------------------------------
    print(f"\n>>>>>>>>>>>>>> START BOOT FOTA PROCESS ON SLAVE {SQ_slave}, MASTER {ID_master}, "
          f"HOST '{UDP_SOCKET.host}', PORT '{UDP_SOCKET.port}'\n") 
    mess_sent = build_start_mess_bootFota_process_slave(ID_master, SQ_slave, addr_start, addr_end)
        
    while retry>0:
        sendto_master(mess_sent, UDP_SOCKET)
        print("-> [Sent] - ", " ".join(f"{b:02X}" for b in mess_sent))
        
        time.sleep(0.001)
        
        result = receive_startBootFota_response_slave(UDP_SOCKET, ID_master, SQ_slave)
        
        if result:
            print(f"-> [Result] - Start Flashing from {hex(addr_start)} to {hex(addr_end)} on SLAVE {SQ_slave} MASTER {ID_master} !")
            return True
        else:
            retry -= 1
            
        time.sleep(0.5)
    print(f"-> [Result] - Start Flashing Process on MASTER {ID_master} Fail !")
    return False

# ======================================================================================================
def flashing_slave_process(ID_master, SQ_slave, UDP_SOCKET={}, _list_hex_data=[], retry=10):
    print(f"\n>>>>>>>>>>>>>> FLASHING  PROCESS ON SLAVE {SQ_slave}, MASTER {ID_master}, "
          f"HOST '{UDP_SOCKET.host}', PORT '{UDP_SOCKET.port}'\n") 
    cnt_line_data = 0
    cnt_error = 0
    start_flash_t = time.time()
    while cnt_line_data < len(_list_hex_data):    
        lenData = len(_list_hex_data[cnt_line_data]['data'])
        mess_flash_data = bytearray(lenData+8)
        
        mess_flash_data[0] = SQ_slave & 0x0F
        mess_flash_data[1] = lenData+8
        mess_flash_data[2] = CMD_FLASHING
        
        mess_flash_data[3] = (_list_hex_data[cnt_line_data]['address'] >> 24) & 0xFF
        mess_flash_data[4] = (_list_hex_data[cnt_line_data]['address'] >> 16) & 0xFF
        mess_flash_data[5] = (_list_hex_data[cnt_line_data]['address'] >> 8) & 0xFF
        mess_flash_data[6] = (_list_hex_data[cnt_line_data]['address'] >> 0) & 0xFF
        
        for j in range(0, len(_list_hex_data[cnt_line_data]['data'])):
            mess_flash_data[j+7] = _list_hex_data[cnt_line_data]['data'][j]
            
        start_send = time.time()
        mess_flash_data[mess_flash_data[1]-1] = crc8(mess_flash_data, mess_flash_data[1])
    
        mess_sent = bytearray(len(mess_flash_data)+3)
        
        # Prepare message to send to Master
        mess_sent[0] = 0xE0 | (ID_master & 0x0F)  # ID Master
        mess_sent[1] = len(mess_flash_data)+3  # Length of message
        for i in range(len(mess_flash_data)):
            mess_sent[i+2] = mess_flash_data[i]
        mess_sent[len(mess_flash_data)+2] = crc8(mess_sent, len(mess_sent))  # CRC
        
        sendto_master(mess_sent, UDP_SOCKET)    
        # print("-> [Sent] - ", " ".join(f"{b:02X}" for b in mess_flash_data))
    
        time.sleep(0.01)
        
        try:
            data_read, _ = UDP_SOCKET.socket.recvfrom(256)
            
            if len(data_read) == 9:
                id_m = data_read[0] & 0x0F
                id_s = data_read[2]   
                cmd = data_read[4]

                if crc8(data_read, len(data_read)) == data_read[-1]     \
                                and id_m == ID_master                   \
                                and cmd == CMD_FLASHING                 \
                                and id_s == SQ_slave:
                    # print("-> Data rec:", " ".join(f"{b:02X}" for b in data_read))
                    
                    rlt = data_read[5]
                    num_byte = data_read[6]
    
                    if rlt == SUCCESS:
                        print(f"-> [Result] - Flashing {num_byte} bytes Success ({round((time.time()-start_send)*1000,1)}ms, "
                            f"{round(cnt_line_data*100/len(_list_hex_data),3)}%)")
                        cnt_line_data+=1
                    else:
                        print(f"-> [Result] - Flashing {num_byte} bytes Fail !")
                        cnt_error+=1
                else:
                    print("-> [Error] - Unexpected response !")
                    cnt_error+=1
            else:
                print("-> [Error] - Response too short !")
                # cnt_error+=1

        except socket.timeout:
            print("-> [Timeout] - Receive Response Timeout !")
            cnt_error+=1
        
        if cnt_error == 10:
            print("\n-> [Error] - Flashing BROKEN and FAIL!\n")
            return False
        
        time.sleep(0.001)

    print(f"\n-> FINISH FLASHING SUCCESS ({round(time.time()-start_flash_t,3)}s) !\n")
    return True

# ======================================================================================================   
def run_Application_fw_slave(ID_master, SQ_slave, UDP_SOCKET, stack_pointer, version, type_circuit, retry=10):
    print(f"\n>>>>>>>>>>>>>> RUN APPLICATION FIRMWARE ON SLAVE {SQ_slave}, MASTER {ID_master}, "
          f"HOST '{UDP_SOCKET.host}, PORT '{UDP_SOCKET.port}'\n")    
    
    date_now = datetime.now()
        
    mess_sent = build_runApp_fw_mess_slave(ID_master, SQ_slave, stack_pointer, version, date_now, type_circuit)

    while retry>0:   
        sendto_master(mess_sent, UDP_SOCKET)    
        print("-> [Sent] - ", " ".join(f"{b:02X}" for b in mess_sent))
    
        time.sleep(0.01)
    
        result = receive_runApp_fw_mess_slave(UDP_SOCKET, ID_master, SQ_slave)
        
        if result:
            print(f"-> [Result] - Run New App Firmware on SLAVE {SQ_slave}, MASTER {ID_master}, version {round(version/10,1)}")
            return True
            
        time.sleep(0.5)
        
    print(f"-> [Result] - Run New App Firmware on SLAVE{SQ_slave}, MASTER {ID_master} Fail !")
    return False

# ======================================================================================================   
def run_bootFOTA_Fw_slave(ID_master, SQ_slave, UDP_SOCKET={}, retry=100):
    # Send FOTA boot command to Master ------------------------------------------------------------
    print(f"\n>>>>>>>>>>>>>> RUN BOOT FOTA FIRMWARE ON SLAVE {SQ_slave}, MASTER {ID_master}, "
          f"HOST '{UDP_SOCKET.host}', PORT '{UDP_SOCKET.port}'\n")
    mess_sent= build_mess_run_bootFOTA_slave(ID_master, SQ_slave)
        
    while retry>0:
        sendto_master(mess_sent, UDP_SOCKET)
        print("-> [Sent] - ", " ".join(f"{b:02X}" for b in mess_sent))
        
        time.sleep(0.01)
        
        result = receive_runFOTA_slave_response(UDP_SOCKET, ID_master, SQ_slave)
        
        if result:
            print(f"-> [Result] - Run Boot FOTA SLAVE {SQ_slave} ON MASTER {ID_master} Success !")
            return True
        else:
            retry -= 1
            
        time.sleep(0.5)
    print(f"-> [Result] - Run Boot FOTA Program on SLAVE {SQ_slave}, MASTER {ID_master} Fail !")
    return False

# ======================================================================================================     
def analysisHex_slaveFW(type="halfword"):
    # Analysing hex file--------------------------------------------------------------------
    print("\n>>>>>>>>>>>>>> ANALYSING HEX FILE   \n")
    
    path_firmware = input("> Enter the path of firmware hex file: ")
    
    if os.path.isfile(path_firmware) == False:
        print(f"-> [Error] - File {path_firmware} not found !")
        path_firmware = "E:\DEV_SPACE__\Github_Desktop_Workspace\Chute_Slave_Fw\Chute_Slave_Fw_v3.5_KV1\MDK-ARM\Chute_Slave_Firmware\Chute_Slave_Firmware.hex"
        print(f"-> [INFOR] - Using default path: {path_firmware}\n")
    
    num_Line, list_data_flash, size_Hex, addr_start, addr_end = analysis_hex(path_firmware, type)

    print(f"-> [INFOR FIRMWARE] - [{type}]")
    print(f"->                  - Number Line: {num_Line}")
    print(f"->                  - Address start Flashing: {hex(addr_start)}")
    print(f"->                  - Address end Flashing: {hex(addr_end)}")
    print(f"->                  - Size program: {size_Hex}", " bytes = ", str(round(size_Hex/1024,2)) + "kB")
    
    return list_data_flash, addr_start, addr_end
 
def log_to_file(log_message: str, filename: str = "result_boot_chute_slave.txt"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{now}] {log_message}\n")
           
#######################################################################################################
#######################################################################################################
#######################################################################################################
#######################################################################################################

def boot_progress(ID_master, SQ_slave, udp_params):
    print(f"\n        -------> BOOTING SLAVE {SQ_slave} on MASTER {ID_master} <------\n")

    mode_current = request_status_slave(ID_master=ID_master, ID_slave=SQ_slave, UDP_SOCKET=udp_params)

    while mode_current == APPLICATION_FW_RUNNING:       # application fw is running on chip
            rlt = run_bootFOTA_Fw_slave(ID_master, SQ_slave, udp_params, retry=5)
            print("\n>>>>>>>>>>>>>> WAIT MCU RESET AND RUNNING BOOT FOTA.... \n") 
            time.sleep(2) 
            mode_current = request_status_slave(ID_master, SQ_slave, UDP_SOCKET=udp_params, retry=5)
            
    if mode_current == BOOTFOTA_FW_RUNNING:
            rlt = True
            
    if rlt == False:
        print("\nxxxxxxxxx SOMETHINGS ERROR - TRY AGAIN xxxxxxxxxxxxx\n")
        time.sleep(3)
        return False
        
    time.sleep(1) 
    # -------------------------------------------------------------------------------------------
    rlt = start_bootFota_process(ID_master, SQ_slave, udp_params, addr_start_flash, addr_end_flash)
        
    if rlt == False:
        print("\nxxxxxxxxx SOMETHINGS ERROR - TRY AGAIN xxxxxxxxxxxxx\n")
        time.sleep(3)
        return False
    
    time.sleep(1)
    # -------------------------------------------------------------------------------------------

    rlt = flashing_slave_process(ID_master, SQ_slave, udp_params, list_hex_data)
    
    if rlt == False:
        print("\nxxxxxxxxx SOMETHINGS ERROR - TRY AGAIN xxxxxxxxxxxxx\n")
        time.sleep(3)
        return False
    
    time.sleep(1)
    # -------------------------------------------------------------------------------------------
    
    rlt = run_Application_fw_slave(ID_master, SQ_slave, udp_params, addr_start_flash, version_slave, SLAVE_CHUTE_CIRCUIT)
    
    if rlt == False:
        print("\nxxxxxxxxx SOMETHINGS ERROR - TRY AGAIN xxxxxxxxxxxxx\n")
        time.sleep(3)
        return False
    
    print("\n>>>>>>>>>>>>>> WAIT MCU RESET AND RUNNING NEW APPLICATION FW.... \n")  
    time.sleep(2)
    
    mode_current = request_status_slave(ID_master, SQ_slave, UDP_SOCKET=udp_params, retry=5)
    
    if mode_current == APPLICATION_FW_RUNNING:
        print(f"\n======> UPDATED NEW APPLICATION ON SLAVE '{SQ_slave}', MASTER '{ID_master}', "
            f"HOST '{HOST_INPUT}', PORT '{PORT_INPUT}' SUCCESS TOTALLY !\n")
        log_to_file(f"SUCCESS: UPDATED NEW APPLICATION ON SLAVE '{SQ_slave}', MASTER '{ID_master}', HOST '{HOST_INPUT}', PORT '{PORT_INPUT}'")

        return True
    else:
        print(f"\nxxxxxx> UPDATED NEW APPLICATION ON SLAVE '{SQ_slave}', MASTER {ID_master}, "
            f"HOST '{HOST_INPUT}', PORT '{PORT_INPUT}' FAILURE xxxxx\n")
        log_to_file(f"FAILURE: UPDATED NEW APPLICATION ON SLAVE '{SQ_slave}', MASTER {ID_master}, HOST '{HOST_INPUT}', PORT '{PORT_INPUT}'")

        return False


#######################################################################################################
#######################################################################################################
#######################################################################################################
#######################################################################################################
if __name__ == "__main__":
    print("\n                          ===============> START PROGRAM <===============\n")
    
    list_hex_data, addr_start_flash, addr_end_flash = analysisHex_slaveFW("word")
    
    time.sleep(1)
    
    print("")
    HOST_INPUT = "192.168.1." + input("> Enter the HOST : 192.168.1." )
    print("")
    PORT_INPUT = int(input("> Enter the PORT : " ))
    print("")
    ID_master = int(input("> Enter ID Master: " ) )
    print("")  
    SQ_slave = int(input(f"> Enter Sequence of Slave in line Master {ID_master}: " ) )
    print("") 
    version_slave = int(input("> Enter the Version Slave: " ))
    print("")
    
    # Tạo socket UDP
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(1)  # Timeout cho việc nhận dữ liệu
    
    udp_params = UdpConnection(udp_socket, HOST_INPUT, PORT_INPUT)
    
    # Reset master before starting
    rlt = reset_master(ID_master=ID_master, UDP_SOCKET=udp_params)
    
    if not rlt:
        exit(1)
        
    time.sleep(1)
    
    # Run mode Forward on MASTER
    run_FWD_master(ID_master=ID_master, UDP_SOCKET=udp_params)
    
    if not rlt:
        reset_master(ID_master=ID_master, UDP_SOCKET=udp_params)
        exit(1)
    
    rlt = boot_progress(ID_master=ID_master, SQ_slave=SQ_slave, udp_params=udp_params)
    
    time.sleep(0.5)
    
    reset_master(ID_master=ID_master, UDP_SOCKET=udp_params)
    
    print("\n                          -------------> CLOSE PROGRAM <-----------\n")
    
    
    