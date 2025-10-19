#include "fuseMod.h"

// CRC16-CCITT 计算函数
uint16_t crc16_ccitt(const uint8_t *data, size_t length) {
    uint16_t crc = 0;
    
    for (size_t i = 0; i < length; i++) {
        crc ^= (uint16_t)data[i] << 8;
        
        for (int j = 0; j < 8; j++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc <<= 1;
            }
        }
    }
    
    return crc;
}

uint8_t *ipath2c(const uint8_t* path, size_t len){
    uint8_t *res = (uint8_t *)malloc(len + 1);
    memcpy(res, path, len);
    res[len] = 0;
    return res;
}

// 验证包格式和CRC
int get_packet_size(const uint8_t *packet, size_t size, uint16_t *type, uint16_t *data_size){
    if (size < PACKET_MIN_SIZE) {
        return ERR_INVALID_PACKET;
    }
 
    // 检查包头
    if (packet[0] != 0x54 || packet[1] != 0x32) {
        return ERR_INVALID_PACKET;
    }

    // 提取类型和数据大小
    *type = (packet[3] << 8) | packet[2];
    *data_size = (packet[5] << 8) | packet[4];

    return 0;
}

int validate_packet(const uint8_t *packet, size_t size, const uint8_t **data) {
    
    // 检查包尾
    if (packet[size - 2] != 0x23 || packet[size - 1] != 0x45) {
        return ERR_INVALID_PACKET;
    }

    uint16_t data_size = (packet[5] << 8) | packet[4];
    
    // 检查数据大小是否匹配
    if (size != PACKET_MIN_SIZE + data_size) {
        return ERR_INVALID_PACKET;
    }
    
    // 提取数据指针
    *data = packet + 6;
    
    // 计算并验证CRC
    uint16_t expected_crc = packet[size - 4] | (packet[size - 3] << 8);
    uint16_t actual_crc = crc16_ccitt(packet, size - 4);

    DEBUG_LOG("C received: ");

    for (int i = 0; i < size; i++){
        DEBUG_LOG("%02x", packet[i]);
    }

    DEBUG_LOG(" %d %02x %02X\n", actual_crc, actual_crc, expected_crc);
    
    if (expected_crc != actual_crc) {
        return ERR_CRC_MISMATCH;
    }
    
    return 0;
}

// 创建响应包
size_t create_response_packet(uint8_t *buffer, uint16_t type, uint16_t data_size, const uint8_t *data) {
    buffer[0] = 0x54;
    buffer[1] = 0x02;
    buffer[2] = type & 0xFF;
    buffer[3] = (type >> 8) & 0xFF;
    buffer[4] = data_size & 0xFF;
    buffer[5] = (data_size >> 8) & 0xFF;
    
    if (data_size > 0 && data != NULL) {
        memcpy(buffer + 6, data, data_size);
    }
    
    // 计算CRC
    uint16_t crc = crc16_ccitt(buffer, 6 + data_size);

    buffer[6 + data_size] = crc & 0xFF;
    buffer[6 + data_size + 1] = (crc >> 8) & 0xFF;
    
    // 添加包尾
    buffer[6 + data_size + 2] = 0x23;
    buffer[6 + data_size + 3] = 0x45;

    DEBUG_LOG("C response: ");
    for (int i = 0; i < 6 + data_size + 4; i++){
        DEBUG_LOG("%02x", buffer[i]);
    }
    DEBUG_LOG(" %d %02x\n", crc, crc);
    
    return 6 + data_size + 4;
}

// 发送错误并退出
void send_error_and_exit(uint8_t error_code, const char *message) {
    #ifdef DEBUG_MODE
    DEBUG_LOG("ERROR: %s\n", message);
    perror("Err");
    #endif
    
    if (pipe_in_fd >= 0){
        close(pipe_in_fd);
    }

    if (pipe_out_fd >= 0){
        close(pipe_out_fd);
    }
    
    kill(0, SIGTERM);
    exit(EXIT_FAILURE);
}

// 路径分割函数
int split_path(const char *path, char ***components) {
    if (path == NULL || path[0] != '/') {
        return -1;
    }
    
    int count = 0;
    const char *start = path + 1;
    const char *end;
    
    // 计算组件数量
    while (*start != '\0') {
        while (*start == '/') start++;
        if (*start == '\0') break;
        
        end = start;
        while (*end != '/' && *end != '\0') end++;
        
        count++;
        start = end;
    }
    
    if (count == 0) {
        return 0;
    }
    
    // 分配内存
    *components = malloc(count * sizeof(char *));
    if (*components == NULL) {
        return -1;
    }
    
    // 提取组件
    start = path + 1;
    for (int i = 0; i < count; i++) {
        while (*start == '/') start++;
        end = start;
        while (*end != '/' && *end != '\0') end++;
        
        int len = end - start;
        (*components)[i] = malloc(len + 1);
        if ((*components)[i] == NULL) {
            for (int j = 0; j < i; j++) {
                free((*components)[j]);
            }
            free(*components);
            return -1;
        }
        
        strncpy((*components)[i], start, len);
        (*components)[i][len] = '\0';
        
        start = end;
    }
    
    return count;
}