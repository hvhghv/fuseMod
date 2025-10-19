#include "fuseMod.h"

void *pipe_listener(void *arg) {
    uint8_t buffer[4096];
    uint8_t response[4096];
    ssize_t bytes_read;
    uint8_t err;
    size_t response_size;

    while ((bytes_read = read(pipe_in_fd, buffer, PACKET_MIN_SIZE)) > 0) {
        uint16_t type, data_size;
        const uint8_t *data;
        int result = ERR_INVALID_PACKET;

        if (bytes_read != PACKET_MIN_SIZE){
            goto bad_packet;
        }

        result = get_packet_size(buffer, bytes_read, &type, &data_size);
        if (result != 0){
            goto bad_packet;
        }

        result = ERR_INVALID_PACKET;
        bytes_read = read(pipe_in_fd, buffer + PACKET_MIN_SIZE, data_size);
        if (bytes_read != data_size){
            goto bad_packet;
        }
 
        result = validate_packet(buffer, bytes_read + PACKET_MIN_SIZE, &data);
        if (result != 0){
            goto bad_packet;
        }
        
        pthread_mutex_lock(&fs_mutex);
        int operation_result = 0;

        switch (type) {
            case 1: { // 创建目录
                if (data_size == 0) {
                    operation_result = ERR_INVALID_PATH;
                } else {
                    uint8_t* cpath = ipath2c(data, data_size);
                    operation_result = create_directory((const char *)cpath);
                    free(cpath);
                }
                break;
            }
            case 2: // 创建可读写文件
            {
                if (data_size < 6) {
                    operation_result = ERR_INVALID_PACKET;
                } else {
                    uint32_t flag = (uint32_t)data[0] | ((uint32_t)data[1] << 8) | ((uint32_t)data[2] << 16) | ((uint32_t)data[3] << 24);
                    uint16_t path_len = (data[5] << 8) | data[4];

                    if ((size_t)(6 + path_len) != data_size) {
                        operation_result = ERR_INVALID_PACKET;
                    } else {
                        uint8_t* cpath = ipath2c(data + 6, path_len);
                        operation_result = create_file((const char *)cpath, flag);
                        free(cpath);
                    }
                }
                break;
            }
            case 3: { // 删除目录
                if (data_size == 0) {
                    operation_result = ERR_INVALID_PATH;
                } else {
                    uint8_t* cpath = ipath2c(data, data_size);
                    operation_result = delete_directory((const char *)data);
                    free(cpath);
                }
                break;
            }
            case 4: { // 删除文件
                if (data_size == 0) {
                    operation_result = ERR_INVALID_PATH;
                } else {
                    uint8_t* cpath = ipath2c(data, data_size);
                    operation_result = delete_file((const char *)data);
                    free(cpath);
                }
                break;
            }
            case 5: { // 设置文件内容
                if (data_size < 4) {
                    operation_result = ERR_INVALID_PACKET;
                } else {
                    uint16_t path_len = (data[1] << 8) | data[0];
                    if (4 + path_len > data_size) {
                        operation_result = ERR_INVALID_PACKET;
                    } else {
                        uint16_t content_len = (data[path_len + 3] << 8) | data[path_len + 2];
                        if (4 + path_len + content_len != data_size) {
                            operation_result = ERR_INVALID_PACKET;
                        } else {
                            char *path_str = malloc(path_len + 1);
                            if (path_str == NULL) {
                                operation_result = ERR_IO_ERROR;
                            } else {
                                memcpy(path_str, data + 2, path_len);
                                path_str[path_len] = '\0';
                                
                                operation_result = set_file_content(
                                    path_str, 
                                    data + 4 + path_len, 
                                    content_len
                                );
                                
                                free(path_str);
                            }
                        }
                    }
                }
                break;
            }
            case 6: { // 追加文件内容
                if (data_size < 4) {
                    operation_result = ERR_INVALID_PACKET;
                } else {
                    uint16_t path_len = (data[1] << 8) | data[0];
                    if (4 + path_len > data_size) {
                        operation_result = ERR_INVALID_PACKET;
                    } else {
                        uint16_t content_len = (data[path_len + 3] << 8) | data[path_len + 2];
                        if (4 + path_len + content_len != data_size) {
                            operation_result = ERR_INVALID_PACKET;
                        } else {
                            char *path_str = malloc(path_len + 1);
                            if (path_str == NULL) {
                                operation_result = ERR_IO_ERROR;
                            } else {
                                memcpy(path_str, data + 2, path_len);
                                path_str[path_len] = '\0';
                                
                                operation_result = append_file_content(
                                    path_str, 
                                    data + 4 + path_len, 
                                    content_len
                                );
                                
                                free(path_str);
                            }
                        }
                    }
                }
                break;
            }

            case 7:
                break;

            default:
                operation_result = ERR_INVALID_TYPE;
                break;
        }
        
        pthread_mutex_unlock(&fs_mutex);
        
        
        err = (uint8_t)operation_result;
        response_size = create_response_packet(
            response, 
            type,
            1, 
            &err
        );
        
        if (write(pipe_out_fd, response, response_size) < 0){
            send_error_and_exit(0, "write pipe_out_fd failed");
        }
        
        if (operation_result != 0) {
            send_error_and_exit(operation_result, "Operation failed");
        }

        continue;
bad_packet:
        err = result;
        response_size = create_response_packet(response, type, 1, &err);
        write(pipe_out_fd, response, response_size);
        break;
    }

    send_error_and_exit(0, "pipe_listener exit");
    return NULL;
}

void create_pipes(const char* in_path, const char* out_path) {
    if (mkfifo(in_path, 0666) != 0 && errno != EEXIST) {
        send_error_and_exit(0, "mkfifo PIPE_IN");
    }
    
    if (mkfifo(out_path, 0666) != 0 && errno != EEXIST) {
        send_error_and_exit(0, "mkfifo PIPE_OUT");
    }
    
    pipe_in_fd = open(in_path, O_RDONLY);
    if (pipe_in_fd < 0) {
        send_error_and_exit(0, "open PIPE_IN");
    }
    
    pipe_out_fd = open(out_path, O_WRONLY);
    if (pipe_out_fd < 0) {
        send_error_and_exit(0, "open PIPE_OUT");
    }
}