#ifndef FUSEMOD_H
#define FUSEMOD_H

#include <fuse3/fuse.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/time.h>
#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdbool.h>
#include <signal.h>

// 错误代码定义
#define ERR_INVALID_PATH 1
#define ERR_ALREADY_EXISTS 2
#define ERR_NOT_FOUND 3
#define ERR_INVALID_OPERATION 4
#define ERR_IO_ERROR 5
#define ERR_INVALID_PACKET 6
#define ERR_CRC_MISMATCH 8
#define ERR_INVALID_TYPE 9

// 包格式常量
#define PACKET_HEADER 0x5432
#define PACKET_TRAILER 0x2345
#define PACKET_MIN_SIZE 10
#define PACKET_MAX_SIZE 3072

#define FLAG_READ (1 << 0)
#define FLAG_WRITE (1 << 1)
#define FLAG_COPY_ON_WRITE (1 << 3)

// 调试模式

#ifdef DEBUG_MODE
#define DEBUG_LOG(...) printf(__VA_ARGS__)
#else
#define DEBUG_LOG(...)
#endif

// 节点类型
typedef enum {
    TYPE_DIR,
    TYPE_FILE
} node_type_t;

// 文件系统节点
typedef struct node {
    char *name;
    node_type_t type;
    mode_t mode;
    uid_t uid;
    gid_t gid;
    char *content;
    size_t size;
    time_t mtime;
    uint32_t flag;
    struct node *parent;
    struct node *children;
    struct node *next;
} node_t;

// 全局变量声明
extern node_t *root;
extern pthread_mutex_t fs_mutex;
extern int pipe_in_fd;
extern int pipe_out_fd;

// CRC函数
uint16_t crc16_ccitt(const uint8_t *data, size_t length);

// 工具函数
uint8_t *ipath2c(const uint8_t* path, size_t len);
int get_packet_size(const uint8_t *packet, size_t size, uint16_t *type, uint16_t *data_size);
int validate_packet(const uint8_t *packet, size_t size, const uint8_t **data);

size_t create_response_packet(uint8_t *buffer, uint16_t type, 
                             uint16_t data_size, const uint8_t *data);
void send_error_and_exit(uint8_t error_code, const char *message);
int split_path(const char *path, char ***components);

// 文件系统操作
node_t *find_node(const char *path);
int create_directory(const char *path);
int create_file(const char *path, uint32_t flag);
int delete_directory(const char *path);
int delete_file(const char *path);
int set_file_content(const char *path, const uint8_t *content, size_t content_size);
int append_file_content(const char *path, const uint8_t *content, size_t content_size);
int write_node_content(node_t *node, const char *buf, size_t size, off_t offset);

// 管道操作
void *pipe_listener(void *arg);
void create_pipes(const char* in_path, const char* out_path);

// FUSE操作
int fusemod_getattr(const char *path, struct stat *stbuf, struct fuse_file_info *fi);
int fusemod_readdir(const char *path, void *buf, fuse_fill_dir_t filler,
                   off_t offset, struct fuse_file_info *fi,
                   enum fuse_readdir_flags flags);
int fusemod_open(const char *path, struct fuse_file_info *fi);
int fusemod_read(const char *path, char *buf, size_t size, off_t offset,
                struct fuse_file_info *fi);
int fusemod_write(const char *path, const char *buf, size_t size, off_t offset,
                 struct fuse_file_info *fi);
// 初始化
void init_filesystem();

#endif