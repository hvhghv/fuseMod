#include "fuseMod.h"

// 全局变量定义
node_t *root = NULL;
pthread_mutex_t fs_mutex = PTHREAD_MUTEX_INITIALIZER;
int pipe_in_fd = -1;
int pipe_out_fd = -1;

static struct fuse_operations fusemod_oper = {
    .getattr = fusemod_getattr,
    .readdir = fusemod_readdir,
    .open = fusemod_open,
    .read = fusemod_read,
    .write = fusemod_write,
};

int main(int argc, char *argv[]) {

    if (argc < 4) {
        fprintf(stderr, "Usage: %s <pipe_in_path> <pipe_out_path> <mount_point> [FUSE options]\n", argv[0]);
        return 1;
    }

    // 初始化文件系统
    init_filesystem();

    // 创建命名管道
    create_pipes(argv[1], argv[2]);
    
    // 创建管道监听线程
    pthread_t listener_thread;
    if (pthread_create(&listener_thread, NULL, pipe_listener, NULL) != 0) {
        send_error_and_exit(0, "Failed to create listener thread");
    }
    
    // 启动 FUSE
    int fuse_result = fuse_main(argc - 2, argv + 2, &fusemod_oper, NULL);
    
    // 清理资源
    close(pipe_in_fd);
    close(pipe_out_fd);
    pthread_cancel(listener_thread);
    pthread_join(listener_thread, NULL);
    
    return fuse_result;
}