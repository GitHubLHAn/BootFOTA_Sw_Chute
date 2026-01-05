# from communication import *
# from readHex import *

import winsound

def parse_intel_hex_line(line):
    """Phân tích một dòng HEX theo chuẩn Intel HEX."""
    if not line.startswith(":"):
        return None

    try:
        line = line.strip()
        length = int(line[1:3], 16)
        address = int(line[3:7], 16)
        record_type = int(line[7:9], 16)
        data = [int(line[i:i+2], 16) for i in range(9, 9 + length * 2, 2)]
        checksum = int(line[9 + length * 2:11 + length * 2], 16)
        
        return {
            "length": length,
            "address": address,
            "type": record_type,
            "data": data,
            "checksum": checksum,
            "raw_line": line
        }
    except Exception as e:
        print(f"Lỗi dòng: {line.strip()} — {e}")
        return None

def parse_hex_file(file_path):
    """Đọc file HEX, lưu từng dòng hợp lệ vào list."""
    hex_lines = []

    with open(file_path, "r") as f:
        for line in f:
            parsed = parse_intel_hex_line(line)
            if parsed:
                hex_lines.append(parsed)

    return hex_lines

def merge_data_pairs(list_halfword):
    list_hex_word = []
    
    # length = len(list_halfword)

    for i in range(0, len(list_halfword),2):
        if i + 1 < len(list_halfword):  # đảm bảo có cặp
            merged_item = {
                "address": list_halfword[i]["address"],
                "data": list_halfword[i]["data"] + list_halfword[i + 1]["data"]
            }
        else:
            merged_item = {
                "address": list_halfword[i]["address"],
                "data": list_halfword[i]["data"]
            }
        list_hex_word.append(merged_item)

    return list_hex_word

def analysis_hex(path_fw, type="halfword"):
    print("-> Path FiwmWare: ", path_fw)
        
    lines_hexFile = parse_hex_file(path_fw)

    num_Line_hexFile = len(lines_hexFile)

    size_off_dataHex = 0
    list_halfword_data = []

    for i, line in enumerate(lines_hexFile):
        if line['type'] == 4:
            # print(line)
            phan_mo_rong_hex = line['data'][0]<<8 | line['data'][1]
            # print(f"-> Phần mở rộng: {hex(phan_mo_rong_hex)}")

        if line['type'] == 0:
            size_off_dataHex += line['length']
            len_last_data = line['length']
            list_halfword_data.append({"address" : (phan_mo_rong_hex<<16) | line['address'], "data" : line['data']}) 
            
    min_address = list_halfword_data[0]['address']
    max_address = min_address

            
    for i, line in enumerate(list_halfword_data):
        if line['address'] > max_address:
            max_address = line['address']            
        if line['address'] < min_address:
            min_address = line['address'] 


    address_start_data = min_address
    address_end_data = max_address+len_last_data-1

    list_word_data = merge_data_pairs(list_halfword_data)
    
    if type == "word":
        list_data_flash = list_word_data
    else:
        list_data_flash = list_halfword_data

    return num_Line_hexFile, list_data_flash, size_off_dataHex, address_start_data, address_end_data
   
    
if __name__ == "__main__":
     # ------------------- Phan tich file hex ------------------------
    print("\n>>> Phân tích file Hex\n")
    
    path_firmware = input("> Nhập vào đường dẫn file hex: ")
    
    num_Line, list_data_flash, size_Hex, addr_start, addr_end = analysis_hex(path_firmware)
    
    print(f"-> Đã phân tích {num_Line} dòng.")
    print("-> Địa chỉ bắt đầu flash: ", hex(addr_start))
    print("-> Địa chỉ kết thúc flash: ", hex(addr_end))

    print("-> Kích thước chương trình firmware = ", str(size_Hex), " bytes = ", str(size_Hex/1024) + " kB")
