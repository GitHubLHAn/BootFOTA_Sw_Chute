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
def crc8(data: bytes, length: int) -> int:
    crc = 0
    for i in range(length - 1):  # Bỏ qua phần tử cuối cùng
        crc ^= data[i]
        for _ in range(8):
            crc = (crc << 1) ^ 0x07 if (crc & 0x80) else (crc << 1)
            crc &= 0xFF  # Giới hạn 8-bit
    return crc


# ======================================================================================================
def sendto_master(data_send:bytearray, UDP_SOCKET):
    UDP_SOCKET.socket.sendto(data_send, (UDP_SOCKET.host, UDP_SOCKET.port))

# ======================================================================================================
def build_mess_reset_master(ID_master:int)->bytearray:
    data_reset = bytearray(4)
    data_reset[0] = 0x60 | (ID_master&0x0F)
    data_reset[1] = 4
    data_reset[2] = 0x06
    data_reset[3] = crc8(data_reset, 4)

    return data_reset

# ======================================================================================================
def receive_reset_master_response(UDP_SOCKET, ID_master):
    try:
        data_read, _ = UDP_SOCKET.socket.recvfrom(256) 
        
        id_m = data_read[0] & 0x0F
        
        if crc8(data_read, len(data_read)) == data_read[-1] \
                                    and id_m == ID_master \
                                    and data_read[0] != 0x00:
            print("-> [Received] - ", " ".join(f"{b:02X}" for b in data_read))
            return True
        else:
            return False
    except socket.timeout:
        print("-> [Timeout] - Timeout Receive Response !")
        return False

# ======================================================================================================
def build_mess_request_status_master(Identify: int)->bytearray:
    status_mess = bytearray(4)
    
    status_mess[0] = 0xB0 | (Identify&0x0F)
    status_mess[1] = 4
    status_mess[2] = 0xA0
    status_mess[3] = crc8(status_mess, 4)
    
    return status_mess

# ======================================================================================================
def receive_status_master(UDP_SOCKET, ID_master):
    try:
        data_read, _ = UDP_SOCKET.socket.recvfrom(256) 
        
        if len(data_read) > 2:
            id_m = data_read[0] & 0x0F
            cmd = data_read[0] & 0xF0
        
        if crc8(data_read, len(data_read)) == data_read[-1]     \
                        and data_read[0] != 0x00                \
                        and id_m == ID_master \
                        and cmd == 0xB0:
            print("-> [Received] - ", " ".join(f"{b:02X}" for b in data_read))
    
            current_mode = data_read[3]
            ver_app = data_read[4]
            day = data_read[5]
            mon = data_read[6]
            year = (data_read[7] << 8) | data_read[8]
            stack_ptr = (data_read[9]<<24) | (data_read[10]<<16) | (data_read[11]<<8) | data_read[12]
            type_circuit = data_read[13]
            
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
    except socket.timeout:
        print("-> [Timeout] - Receive Response Timeout !")
        return False, False

# ======================================================================================================
def build_mess_run_bootFOTA_master(Identify: int) -> bytearray:
    runFOTA_mess = bytearray(4)
    
    runFOTA_mess[0] = 0xC0 | (Identify & 0x0F)  # Byte đầu tiên
    runFOTA_mess[1] = 4                         # Độ dài gói
    runFOTA_mess[2] = 0x0C                      # Mã lệnh
    runFOTA_mess[3] = crc8(runFOTA_mess, 4)     # CRC8 checksum
    
    return runFOTA_mess

# ======================================================================================================
def receive_runFOTA_master_response(UDP_SOCKET, ID_master):
    try:
        data_read, _ = UDP_SOCKET.socket.recvfrom(256)
        
        if len(data_read) > 2:
            id_m = data_read[0] & 0x0F
            cmd = data_read[0] & 0xF0
        
        # Kiểm tra CRC và byte phản hồi hợp lệ
        if crc8(data_read, len(data_read)) == data_read[-1] \
                                    and cmd == 0xC0 \
                                    and id_m == ID_master \
                                    and data_read[0] != 0x00 :
            
            print("-> [Received] - ", " ".join(f"{b:02X}" for b in data_read))
            
            if data_read[3] == SUCCESS:
                return True
        else:
            print("-> [Error] - Unexpected Response!")
            return False

    except socket.timeout:
        print("-> [Timeout] - Receive Response Timeout !")
        return False

# ======================================================================================================
def build_start_mess_bootFota_process(Identify: int, addr_start, addr_end)->bytearray:
    mess_start_boot = bytearray(12)
    
    mess_start_boot[0] = Identify & 0x0F                 
    mess_start_boot[1] = 12                        
    mess_start_boot[2] = CMD_START_FLASHING        
    mess_start_boot[3] =  (addr_start >> 24)  & 0xFF                  
    mess_start_boot[4] =  (addr_start >> 16)  & 0xFF                        
    mess_start_boot[5] =  (addr_start >> 8)  & 0xFF                           
    mess_start_boot[6] =  (addr_start)  & 0xFF                           
    mess_start_boot[7] =  (addr_end >> 24)  & 0xFF                     
    mess_start_boot[8] =  (addr_end >> 16)  & 0xFF                        
    mess_start_boot[9] =  (addr_end >> 8)  & 0xFF                          
    mess_start_boot[10] = (addr_end)  & 0xFF                        
    mess_start_boot[11] = crc8(mess_start_boot, mess_start_boot[1])  
    
    return mess_start_boot

# ======================================================================================================
def receive_startBootFota_response(UDP_SOCKET, ID_master):
    try:
        data_read, _ = UDP_SOCKET.socket.recvfrom(256)
        
        if len(data_read) > 2:
            id_m = data_read[0] & 0x0F
            cmd = data_read[2]
        
        # Kiểm tra CRC và byte phản hồi hợp lệ
        if crc8(data_read, len(data_read)) == data_read[-1] \
                                    and cmd == CMD_START_FLASHING \
                                    and id_m == ID_master \
                                    and data_read[0] != 0x00 :            
            print("-> [Received] - ", " ".join(f"{b:02X}" for b in data_read))
            rlt = data_read[3]                  # result
            num_page = data_read[4]
            
            if rlt == SUCCESS:
                print(f"-> [Result] - Erased {num_page} pages on Master {id_m}. Start Flashing Success !")
                return True
            else:
                print("-> [Result] - Erased Fail. Start Flashing Fail !")
        else:
            print("-> [Error] - Unexpected Response!")
            return False

    except socket.timeout:
        print("-> [Timeout] - Receive Response Timeout !")
        return False
    
# ======================================================================================================
def build_runApp_fw_mess(Identify, stack_pointer, version, _date_now, type_circuit)->bytearray:
        mess_run_app = bytearray(14)
        
        mess_run_app[0] = Identify & 0x0F
        mess_run_app[1] = 14
        mess_run_app[2] = CMD_RUN_APP
        
        mess_run_app[3] = (stack_pointer >> 24) & 0xFF
        mess_run_app[4] = (stack_pointer >> 16) & 0xFF
        mess_run_app[5] = (stack_pointer >> 8) & 0xFF
        mess_run_app[6] = (stack_pointer >> 0) & 0xFF
        
        mess_run_app[7] = version & 0xFF
        
        mess_run_app[8] = _date_now.day & 0xFF
        mess_run_app[9] = _date_now.month & 0xFF
        mess_run_app[10] = (_date_now.year>>8) & 0xFF
        mess_run_app[11] = _date_now.year & 0xFF
        mess_run_app[12] = type_circuit
        
        mess_run_app[mess_run_app[1]-1] = crc8(mess_run_app, mess_run_app[1])
        
        return mess_run_app

# ======================================================================================================
def receive_runApp_fw_mess(UDP_SOCKET, ID_master):
    try:
        data_read, _ = UDP_SOCKET.socket.recvfrom(256)
        
        if len(data_read) > 2:
            id_m = data_read[0] & 0x0F
            cmd = data_read[2]

        if crc8(data_read, len(data_read)) == data_read[-1] \
                                    and data_read[0] != 0x00 \
                                    and id_m == ID_master \
                                    and cmd == CMD_RUN_APP:
            print("-> [Received] - ", " ".join(f"{b:02X}" for b in data_read))
            rlt = data_read[3]

            if rlt == SUCCESS:
                # print(f"-> Send Command Run Application Fw on Master {ID_master_input} SUCCESS !")
                return True
            else:
                # print(f"-> Send Command Run Application Fw on Master {ID_master_input} FAILURE !")
                return False
        else:
            print("-> [Error] - Unexpected response !")
            return False

    except socket.timeout:
        print("-> Timeout Response !")

#######################################################################################################
#######################################################################################################
#######################################################################################################
#######################################################################################################

def reset_master(ID_master, retry=100, UDP_SOCKET={}):
    # Send reset mess to Master----------------------------------------------------------------------
    print(f"\n>>>>>>>>>>>>>> RESET MASTER {ID_master}, HOST '{UDP_SOCKET.host}', "
          f"PORT '{UDP_SOCKET.port}'\n")
    mess_reset = build_mess_reset_master(ID_master)
    
    while retry>=0:
        sendto_master(mess_reset, UDP_SOCKET)
        print("-> [Sent] - ", " ".join(f"{b:02X}" for b in mess_reset))
        
        time.sleep(0.01)
        
        result = receive_reset_master_response(UDP_SOCKET, ID_master)
        
        if result:
            print(f"-> [Result] - Reset MASTER {ID_master} Success !")
            return True
        else:
            retry -= 1
        time.sleep(0.5)
    print(f"-> [Result] - Reset MASTER {ID_master} Fail !")
    return False

# ======================================================================================================
def request_status_master(ID_master, UDP_SOCKET={}, retry=100):
    # 
    print(f"\n>>>>>>>>>>>>>> REQUEST STATUS MASTER {ID_master}, "
            f"HOST '{UDP_SOCKET.host}', PORT '{UDP_SOCKET.port}'\n")
    mess_status = build_mess_request_status_master(ID_master)
    while retry>0:
        sendto_master(mess_status, UDP_SOCKET)
        print("-> [Sent] - ", " ".join(f"{b:02X}" for b in mess_status))
        
        time.sleep(0.01)
        
        current_mode, result = receive_status_master(UDP_SOCKET, ID_master)
        
        if result:
            return current_mode
        else:
            retry -= 1
            
        time.sleep(0.5)
        
    print(f"-> [Result] - Request Status MASTER {ID_master} Fail !")
    return False
    
# ======================================================================================================   
def run_bootFOTA_Fw_master(ID_master, UDP_SOCKET={}, retry=100):
    # Send FOTA boot command to Master ------------------------------------------------------------
    print(f"\n>>>>>>>>>>>>>> RUN BOOT FOTA FIRMWARE ON MASTER {ID_master}, "
          f"HOST '{UDP_SOCKET.host}', PORT '{UDP_SOCKET.port}'\n")
    mess_fota = build_mess_run_bootFOTA_master(ID_master)
        
    while retry>0:
        sendto_master(mess_fota, UDP_SOCKET)
        print("-> [Sent] - ", " ".join(f"{b:02X}" for b in mess_fota))
        
        time.sleep(0.01)
        
        result = receive_runFOTA_master_response(UDP_SOCKET, ID_master)
        
        if result:
            print(f"-> [Result] - Run Boot FOTA MASTER {ID_master} Success !")
            return True
        else:
            retry -= 1
            
        time.sleep(0.5)
    print(f"-> [Result] - Run Boot FOTA Program on MASTER {ID_master} Fail !")
    return False

# ======================================================================================================
def start_bootFota_process(ID_master, UDP_SOCKET={}, addr_start=0, addr_end=0, retry=100):
    # Send start boot command to Master ------------------------------------------------------------
    print(f"\n>>>>>>>>>>>>>> START BOOT FOTA PROCESS ON MASTER {ID_master}, "
          f"HOST '{UDP_SOCKET.host}, PORT '{UDP_SOCKET.port}'\n") 
    mess_start = build_start_mess_bootFota_process(ID_master, addr_start, addr_end)
        
    while retry>0:
        sendto_master(mess_start, UDP_SOCKET)
        print("-> [Sent] - ", " ".join(f"{b:02X}" for b in mess_start))
        
        time.sleep(0.01)
        
        result = receive_startBootFota_response(UDP_SOCKET, ID_master)
        
        if result:
            print(f"-> [Result] - Start Flashing from {hex(addr_start)} to {hex(addr_end)} on MASTER {ID_master} !")
            return True
        else:
            retry -= 1
            
        time.sleep(0.5)
    print(f"-> [Result] - Start Flashing Process on MASTER {ID_master} Fail !")
    return False

# ======================================================================================================
def flashing_master_process(ID_master, UDP_SOCKET={}, _list_hex_data=[], retry=10):
    print(f"\n>>>>>>>>>>>>>> FLASHING  PROCESS ON MASTER {ID_master}, "
          f"HOST '{UDP_SOCKET.host}', PORT '{UDP_SOCKET.port}'\n") 
    cnt_line_data = 0
    cnt_error = 0
    start_flash_t = time.time()
    while cnt_line_data < len(_list_hex_data):    
        lenData = len(_list_hex_data[cnt_line_data]['data'])
        mess_flash_data = bytearray(lenData+8)
        
        mess_flash_data[0] = ID_master & 0x0F
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
    
        sendto_master(mess_flash_data, UDP_SOCKET)    
        # print("-> [Sent] - ", " ".join(f"{b:02X}" for b in mess_flash_data))
    
        time.sleep(0.01)
        
        try:
            data_read, _ = UDP_SOCKET.socket.recvfrom(256)
            
            if len(data_read) > 2:
                id_m = data_read[0] & 0x0F
                cmd = data_read[2]

            if crc8(data_read, len(data_read)) == data_read[-1]     \
                            and id_m == ID_master                   \
                            and cmd == CMD_FLASHING                 \
                            and data_read[0] != 0x00:
                # print("-> Data rec:", " ".join(f"{b:02X}" for b in data_read))
                
                rlt = data_read[3]
                num_byte = data_read[4]
   
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
def run_Application_fw_master(ID_master, UDP_SOCKET, stack_pointer, version, type_circuit, retry=10):
    print(f"\n>>>>>>>>>>>>>> RUN APPLICATION FIRMWARE ON MASTER {ID_master}, "
          f"HOST '{UDP_SOCKET.host}, PORT '{UDP_SOCKET.port}'\n")    
    
    date_now = datetime.now()
        
    mess_run_app = build_runApp_fw_mess(ID_master, stack_pointer, version, date_now, type_circuit)

    while retry>0:   
        sendto_master(mess_run_app, UDP_SOCKET)    
        print("-> [Sent] - ", " ".join(f"{b:02X}" for b in mess_run_app))
    
        time.sleep(0.01)
    
        result = receive_runApp_fw_mess(UDP_SOCKET, ID_master)
        
        if result:
            print(f"-> [Result] - Run New App Firmware on MASTER {ID_master}, version {round(version/10,1)}")
            return True
            
        time.sleep(0.5)
        
    print(f"-> [Result] - Run New App Firmware on MASTER {ID_master} Fail !")
    return False

# ======================================================================================================     
def analysisHex_masterFW(type="halfword"):
    # Analysing hex file--------------------------------------------------------------------
    print("\n>>>>>>>>>>>>>> ANALYSING HEX FILE   \n")
    

    path_firmware = input("> Enter the path of MASTER firmware hex file: ")
    
    if os.path.isfile(path_firmware) == False:
        print(f"-> [Error] - File {path_firmware} not found !")
        path_firmware = "E:\DEV_SPACE__\Github_Desktop_Workspace\Chute_Master_Fw\Chute_Master_FW_v4.2\MDK-ARM\Chute_Master_Firmware\Chute_Master_Firmware.hex"
        print(f"-> [INFOR] - Using default path: {path_firmware}\n")
    
    num_Line, list_data_flash, size_Hex, addr_start, addr_end = analysis_hex(path_firmware, type)

    print(f"-> [INFOR FIRMWARE] - [{type}]")
    print(f"->                  - Number Line: {num_Line}")
    print(f"->                  - Address start Flashing: {hex(addr_start)}")
    print(f"->                  - Address end Flashing: {hex(addr_end)}")
    print(f"->                  - Size program: {size_Hex}", " bytes = ", str(round(size_Hex/1024,2)) + "kB")
    
    return list_data_flash, addr_start, addr_end
    
def log_to_file(log_message: str, filename: str = "result_boot_chute_master.txt"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{now}] {log_message}\n")
              
#######################################################################################################
#######################################################################################################
#######################################################################################################
#######################################################################################################

if __name__ == "__main__":
    print("\n                          -------------> BOOT FOTA MASTER <-----------\n")
    
    list_hex_data, addr_start_flash, addr_end_flash = analysisHex_masterFW("word")
    
    time.sleep(1)
    
    print("")
    HOST_INPUT = "192.168.1." + input("> Enter the HOST : 192.168.1." )
    print("")
    PORT_INPUT = int(input("> Enter the PORT : " ))
    print("")
    qty_master = int(input("> Enter Quantity Master Boot: " ) )
    print("")
    ID_master_start = int(input("> Enter the First ID Master: " ) )
    print("")  
    version_master = int(input("> Enter the Version Master: " ))
    print("")
    
    # Tạo socket UDP
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(1)  # Timeout cho việc nhận dữ liệu
    
    udp_params = UdpConnection(udp_socket, HOST_INPUT, PORT_INPUT)
    
    ID_master_input = ID_master_start
    rlt = True
    while ID_master_input <= ID_master_start+qty_master-1:
        # Start Booting by FOTA *****************************
        ctn = "1"
        while ctn != "":
            ctn = input(f"\n> Press Enter to continue to BOOT FOTA PROCESS on MASTER {ID_master_input} ...")

        mode_current = request_status_master(ID_master=ID_master_input, UDP_SOCKET=udp_params)
            
        while mode_current == APPLICATION_FW_RUNNING:       # application fw is running on chip
            rlt = run_bootFOTA_Fw_master(ID_master_input, udp_params, retry=5)
            print("\n>>>>>>>>>>>>>> WAIT MCU RESET AND RUNNING BOOT FOTA.... \n") 
            time.sleep(2) 
            mode_current = request_status_master(ID_master=ID_master_input, UDP_SOCKET=udp_params, retry=100)
            
        if mode_current == BOOTFOTA_FW_RUNNING:
            rlt = True
                   
        if rlt == False:
            print("\nxxxxxxxxx SOMETHINGS ERROR - TRY AGAIN xxxxxxxxxxxxx\n")
            time.sleep(3)
            continue
        
        time.sleep(1) 
        # -------------------------------------------------------------------------------------------
        
        rlt = start_bootFota_process(ID_master_input, udp_params, addr_start_flash, addr_end_flash)
        
        if rlt == False:
            print("\nxxxxxxxxx SOMETHINGS ERROR - TRY AGAIN xxxxxxxxxxxxx\n")
            time.sleep(3)
            continue
        
        time.sleep(1)
        # -------------------------------------------------------------------------------------------
        

        rlt = flashing_master_process(ID_master_input, udp_params, list_hex_data)
        
        if rlt == False:
            print("\nxxxxxxxxx SOMETHINGS ERROR - TRY AGAIN xxxxxxxxxxxxx\n")
            time.sleep(3)
            continue
        
        time.sleep(1)
        # -------------------------------------------------------------------------------------------
        
        
        rlt = run_Application_fw_master(ID_master_input, udp_params, addr_start_flash, version_master, MASTER_CHUTE_CIRCUIT)
        
        if rlt == False:
            print("\nxxxxxxxxx SOMETHINGS ERROR - TRY AGAIN xxxxxxxxxxxxx\n")
            time.sleep(3)
            continue
        
        print("\n>>>>>>>>>>>>>> WAIT MCU RESET AND RUNNING NEW APPLICATION FW.... \n")  
        time.sleep(2)
        
        mode_current = request_status_master(ID_master=ID_master_input, UDP_SOCKET=udp_params)
        
        if mode_current == APPLICATION_FW_RUNNING:
            print(f"\n======> UPDATED NEW APPLICATION ON MASTER '{ID_master_input}', "
                f"HOST '{HOST_INPUT}', PORT '{PORT_INPUT}' SUCCESS TOTALLY !\n")
            log_to_file(f"SUCCESS: UPDATED NEW APPLICATION ON MASTER '{ID_master_input}', HOST '{HOST_INPUT}', PORT '{PORT_INPUT}'")

            ID_master_input += 1
        else:
            print(f"\nxxxxxx> UPDATED NEW APPLICATION ON MASTER {ID_master_input}, "
                f"HOST '{HOST_INPUT}', PORT '{PORT_INPUT}' FAILURE xxxxx\n")
            log_to_file(f"FAILURE: UPDATED NEW APPLICATION ON MASTER '{ID_master_input}', HOST '{HOST_INPUT}', PORT '{PORT_INPUT}'")
        
        time.sleep(5)
    
    print("\n                          -------------> CLOSE PROGRAM <-----------\n")


