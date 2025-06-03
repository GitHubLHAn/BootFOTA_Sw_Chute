import socket
import random
import time
import keyboard

# Thông tin máy chủ
HOST = "192.168.1.200"
PORT = 1111


# number_slave = 21
# ID_master = 0x01

# HOST = input("\n> Nhập vào IP 3one: ")
# PORT = int(input("\n> Nhập vào Port 3one cần test: "))

number_slave = 1

ID_master = int(input("\n> Nhập ID MASTER cần test: "))
cnt_down = 0


print("\n******************* BẮT ĐẦU *******************\n")

while cnt_down > 0:
    print(f"-> Run after {cnt_down} seconds left!")
    cnt_down -= 1
    time.sleep(1)

vRunApp = True

hanoi_districts = [
    "BaDinh", "HoanKiem", "TayHo", "LongBien", "CauGiay",
    "DongDa", "HaiBaTrung", "HoangMai", "ThanhXuan",
    "SocSon", "DongAnh", "GiaLam", "ThanhTri", "BacTuLiem",
    "NamTuLiem", "HaDong", "SonTay", "BaVi", "ChuongMy",
    "DanPhuong", "HoaiDuc", "MeLinh", "PhuXuyen", "PhucTho",
    "QuocOai", "ThachThat", "UngHoa", "MyDuc"
]

# Tính CRC-8
def crc8(data: bytes, length: int) -> int:
    crc = 0
    for i in range(length - 1):  # Bỏ qua phần tử cuối cùng
        crc ^= data[i]
        for _ in range(8):
            crc = (crc << 1) ^ 0x07 if (crc & 0x80) else (crc << 1)
            crc &= 0xFF  # Giới hạn 8-bit
    return crc

#***********************************************************************************************
if __name__ == "__main__":
    # Tạo socket UDP
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(0.3)  # Timeout cho việc nhận dữ liệu

    s_time = time.time()
    # ======================== Gửi Reset ===========================
    data_reset = bytearray(4)
    data_reset[0] = 0x60 | (ID_master&0x0F)
    data_reset[1] = 4
    data_reset[2] = 0x06
    data_reset[3] = crc8(data_reset, 4)

    while True:
        udp_socket.sendto(data_reset, (HOST, PORT))
        print("Data Reset sent:", " ".join(f"{b:02X}" for b in data_reset))
        
        time.sleep(0.01)

        try:
            data_read, _ = udp_socket.recvfrom(256)
            if crc8(data_read, len(data_read)) == data_read[-1] and data_read[0] != 0x00:
                print("Reset thành công!")
                print("Data rec:", " ".join(f"{b:02X}" for b in data_read))
                break
            else:
                print("Reset thất bại!")
        except socket.timeout:
            print("Timeout khi nhận phản hồi Reset")
            vRunApp = False

        time.sleep(0.5)

    time.sleep(1)
    print("")
    
    # ======================== Config Slave ===========================

    cnt_slave_config = 1
    
    
    cnt_db = 0
    
    while cnt_slave_config < (number_slave+1):
    # Chuẩn bị gói tin gửi
        data_config = bytearray(20)
        # print(len(data_config))
        random_district = hanoi_districts[cnt_slave_config]
        # print(random_district)
        so = random.randint(1000, 1999)
        str_name = random_district + "_" + str(so)
        config_buf = bytearray(str_name.encode())

        config_str = config_buf[:15]  
        config_str.extend(b'\x00' * (15 - len(config_str)))
    
        data_config[0] = 0x10 | (ID_master&0x0F)
        data_config[1] = 20
        data_config[2] = cnt_slave_config
        data_config[3:18] = config_str  # Chèn dữ liệu cấu hình
        data_config[18] = 0xA6
        data_config[19] = crc8(data_config, 20)
        
        # print(len(data_config))
        
        udp_socket.sendto(data_config, (HOST, PORT))
        print("Data Config sent:", " ".join(f"{b:02X}" for b in data_config))
        
        if cnt_db == 10:
            cnt_db = 0
            cnt_slave_config += 1

        time.sleep(0.2)
        
        # Nhận phản hồi từ slave, kiểm tra phản hồi thành công hay timeout
        try:
            data_read, _ = udp_socket.recvfrom(1024)
            
            id_master_res = data_read[0] & 0x0F
            command_res = data_read[0] & 0xF0
            
            stt_slave_res = data_read[2]
                
            # Kiểm tra CRC và độ dài của bản tin nhận
            if crc8(data_read, len(data_read)) == data_read[-1] and \
                len(data_read) == data_read[1] and (data_read[0]) and \
                    command_res == 0x10 and stt_slave_res>0 and \
                    stt_slave_res<=number_slave and \
                    stt_slave_res == cnt_slave_config:
                # print(stt_save_res)
                print(f"Config Slave {stt_slave_res} on Master {id_master_res} Success...", " ".join(f"{b:02X}" for b in data_read))
                
                # formatted_hex = " ".join(f"{b:02X}" for b in data_read)
                # print("Data Config Response:", formatted_hex)
                
                cnt_slave_config+=1
            else:
                print(f"-> Config Slave {cnt_slave_config} Fail - ", " ".join(f"{b:02X}" for b in data_read))
                cnt_db += 1
        except socket.timeout:
            print(f"Timeout Config Slave {cnt_slave_config}...")
            cnt_db += 1
        
        time.sleep(0.5)
        # cnt_slave_config+=1

    time.sleep(0.5)
    print("")
    
    # ======================== Gửi Enable ===========================
    data_enable = bytearray(number_slave + 3)
    data_enable[0] = 0x20 | (ID_master&0x0F)
    data_enable[1] = number_slave + 3
    data_enable[2:number_slave + 2] = bytes(range(1, number_slave + 1))
    data_enable[number_slave + 2] = crc8(data_enable, len(data_enable))

    udp_socket.sendto(data_enable, (HOST, PORT))
    print("Data Enable sent:", " ".join(f"{b:02X}" for b in data_enable))

    try:
        data_read, _ = udp_socket.recvfrom(1024)
        # print(f"Received ({len(data_read)} bytes):", " ".join(f"{b:02X}" for b in data_read))
        if crc8(data_read, len(data_read)) == data_read[-1]:
            print("Enable thành công!")
        else:
            print("Enable thất bại!")
    except socket.timeout:
        print("Timeout khi nhận phản hồi Enable")
        vRunApp = False

    time.sleep(0.5)
    print("")
    

    # ======================== Gửi Token liên tục ===========================
    solangui = 0
    solannhan = 0
    solannhandung = 0
    t_tran_max = 0
    last_time = time.time()
    cycle = 0.05  # Chu kỳ gửi 50ms
    
    flag_disable_master = False
    
    statusChute_manage = [0] * (number_slave + 1)
    fullChute_manage = [0] * (number_slave + 1)
    disconectChute_manage = [0] * (number_slave + 1)
    
    qty_packet = 0
    
    last_increase_qty = time.time()

    print("Bắt đầu gửi dữ liệu... Nhấn 'q' để thoát")

    while vRunApp:
        time.sleep(0.001)
        if keyboard.is_pressed('q'):
            print("Đã thoát!")
            break
        
        if (time.time()-last_increase_qty) >= 1:
            qty_packet += 1
            if qty_packet > 255:
                qty_packet = 0
            last_increase_qty = time.time()

        # --------------------------------------------------
        current_time = time.time()
        if current_time - last_time > cycle and flag_disable_master == False:
            qty_bytes = number_slave * 2 + 4
            data_token = bytearray(qty_bytes)
            

            data_token[0] = 0x30 | (ID_master&0x0F)
            data_token[1] = qty_bytes
            offset = 2
            for i in range(1, number_slave + 1):
                data_token[offset] = (statusChute_manage[i] & 0xC0) | (i & 0x3F)
                data_token[offset + 1] = qty_packet
                offset += 2

            signal_full = any(value == 0x01 for value in fullChute_manage)
            signal_disconnect = any(value == 0x01 for value in disconectChute_manage)
            
            data_token[-2] = 0x04   # bat den xanh
            if signal_disconnect:
                # print("Co mot mang nao do mat ket noi")
                data_token[-2] = (data_token[-2]&0xCF) | 0x30   # toogle slow yellow
            if signal_full:
                # print("Co mot mang nao do day")
                data_token[-2] = (data_token[-2]&0xCF) | 0x20   # toogle slow yellow
                data_token[-2] = data_token[-2]&0xF3            # clear green
                data_token[-2] = (data_token[-2]&0xFC) | 0x02   # toggle slow speaker           
            
            
            data_token[-1] = crc8(data_token, qty_bytes)

            udp_socket.sendto(data_token, (HOST, PORT))
            solangui += 1
            # if solangui > 1000:
            #     solangui = 0
            
            last_time = time.time()

        # Nhận phản hồi--------------------------------------------------
        try:
            data_read, _ = udp_socket.recvfrom(256)          
            solannhan += 1

            if crc8(data_read, len(data_read)) == data_read[-1] and len(data_read) == data_read[1]:
                # formatted_hex = " ".join(f"{b:02X}" for b in data_read)
                # print(f"Nhận phản hồi ({len(data_read)} bytes): {formatted_hex}")
                # print("Bản tin hợp lệ!")
                solannhandung += 1
                t_tran_max = max(t_tran_max, time.time() - last_time)
                
                id_master_res = data_read[0] & 0x0F
                command_res = data_read[0] & 0xF0
                
                # Neu nhan ban tin disable tu master
                if len(data_read) == 4 and command_res == 0x70 and (data_read[2] == 0x07):
                    master_lost = id_master_res
                    flag_disable_master = True
                    print(f"Master {master_lost} chua duoc enable")
                
                #
                if command_res == 0x30:
                    # print("Status response mess")
                    
                    for i in range(2, len(data_read) - 2, 2):  # Duyệt từng cặp giá trị
                        slave_id = data_read[i]
                        
                        disconectChute_manage[slave_id] = (data_read[i + 1] >> 2) & 0x01
                        bt = (data_read[i + 1] >> 1) & 0x01
                        fullChute_manage[slave_id] = (data_read[i + 1] >> 0) & 0x01
                        
                        if disconectChute_manage[slave_id] == 0x01:
                            print(f"Mất kết nối đến Slave {slave_id} tại Master {id_master_res}")
                            
                        if bt == 0x01:
                            # print(f"Có tín hiệu nút nhấn từ Slave {slave_id} tại Master {id_master_res}")
                            if statusChute_manage[slave_id] == 0x00:
                                statusChute_manage[slave_id] = 0x40
                                print(f"Nhấn nút Đóng máng {slave_id} tại Master {id_master_res}")
                            elif statusChute_manage[slave_id] == 0x40:
                                statusChute_manage[slave_id] = 0x00
                                print(f"Nhấn nút Mở máng {slave_id} tại Master {id_master_res}")
                            
                        if fullChute_manage[slave_id] == 0x01:
                            print(f"Slave {slave_id} tại Master {id_master_res} đầy....")

        except socket.timeout:
            pass  # Không có dữ liệu thì tiếp tục gửi
        
        # Nhận phản hồi--------------------------------------------------
        if flag_disable_master:
            print(f"Enable master {master_lost} again...")
            # flag_disable_master = False  # Reset lại cờ sau khi xử lý

            # Tạo lại gói Enable
            data_enable = bytearray(number_slave + 3)
            data_enable[0] = 0x20 | (master_lost & 0x0F)
            data_enable[1] = number_slave + 3
            data_enable[2:number_slave + 2] = bytes(range(1, number_slave + 1))
            data_enable[number_slave + 2] = crc8(data_enable, len(data_enable))

            udp_socket.sendto(data_enable, (HOST, PORT))
            # print("Data Enable resent:", " ".join(f"{b:02X}" for b in data_enable))
            
            try:
                data_read, _ = udp_socket.recvfrom(1024)
                if crc8(data_read, len(data_read)) == data_read[-1]:
                    print(f"Enable master {master_lost} again Success...")
                    flag_disable_master = False
                else:
                    print(f"Enable master {master_lost} again Fail...")
            except socket.timeout:
                print(f"Time out Enable master {master_lost} again...")
                
            time.sleep(0.2)

    # ======================== Kết thúc ===========================
    print("Chu kỳ gửi (ms):", cycle * 1000)
    print("Số lần gửi:", solangui+1)
    print("Số lần nhận:", solannhan)
    print("Số lần nhận đúng:", solannhandung)
    print("Tỷ lệ nhận đúng:", (solannhandung/solangui)* 100 if solangui > 0 else 0)
    print("Thời gian truyền nhận tối đa:", t_tran_max)



    udp_socket.close()
