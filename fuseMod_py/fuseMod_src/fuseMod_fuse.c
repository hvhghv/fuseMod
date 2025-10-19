#include "fuseMod.h"

// FUSE 操作实现
int fusemod_getattr(const char *path, struct stat *stbuf, struct fuse_file_info *fi) {
    (void) fi;
    
    pthread_mutex_lock(&fs_mutex);
    node_t *node = find_node(path);
    
    if (node == NULL) {
        pthread_mutex_unlock(&fs_mutex);
        return -ENOENT;
    }
    
    memset(stbuf, 0, sizeof(struct stat));
    stbuf->st_uid = node->uid;
    stbuf->st_gid = node->gid;
    stbuf->st_mtime = node->mtime;
    
    if (node->type == TYPE_DIR) {
        stbuf->st_mode = node->mode;
        stbuf->st_nlink = 2;
    } else {
        stbuf->st_mode = node->mode;
        stbuf->st_nlink = 1;
        stbuf->st_size = node->size;
    }
    
    pthread_mutex_unlock(&fs_mutex);
    return 0;
}

int fusemod_readdir(const char *path, void *buf, fuse_fill_dir_t filler,
                           off_t offset, struct fuse_file_info *fi,
                           enum fuse_readdir_flags flags) {
    (void) offset;
    (void) fi;
    (void) flags;
    
    pthread_mutex_lock(&fs_mutex);
    node_t *node = find_node(path);
    
    if (node == NULL || node->type != TYPE_DIR) {
        pthread_mutex_unlock(&fs_mutex);
        return -ENOENT;
    }
    
    filler(buf, ".", NULL, 0, 0);
    filler(buf, "..", NULL, 0, 0);
    
    node_t *child = node->children;
    while (child != NULL) {
        filler(buf, child->name, NULL, 0, 0);
        child = child->next;
    }
    
    pthread_mutex_unlock(&fs_mutex);
    return 0;
}

int fusemod_open(const char *path, struct fuse_file_info *fi) {
    pthread_mutex_lock(&fs_mutex);
    node_t *node = find_node(path);
    
    if (node == NULL) {
        pthread_mutex_unlock(&fs_mutex);
        return -ENOENT;
    }
    
    if (node->type == TYPE_DIR) {
        pthread_mutex_unlock(&fs_mutex);
        return -EISDIR;
    }
    
    // 检查权限

    int accmode = fi->flags & O_ACCMODE;
    if (accmode == O_RDONLY || accmode == O_RDWR) {
        if ((node->flag & FLAG_READ) == 0) {
            pthread_mutex_unlock(&fs_mutex);
            return -EACCES;
        }
    }
    
    if (accmode == O_WRONLY || accmode == O_RDWR) {
        if ((node->flag & FLAG_WRITE) == 0) {
            pthread_mutex_unlock(&fs_mutex);
            return -EACCES;
        }
    }

    
    pthread_mutex_unlock(&fs_mutex);
    return 0;
}

int fusemod_read(const char *path, char *buf, size_t size, off_t offset,
                        struct fuse_file_info *fi) {
    (void) fi;
    
    pthread_mutex_lock(&fs_mutex);
    node_t *node = find_node(path);
    
    if (node == NULL) {
        pthread_mutex_unlock(&fs_mutex);
        return -ENOENT;
    }
    
    if (node->type == TYPE_DIR) {
        pthread_mutex_unlock(&fs_mutex);
        return -EISDIR;
    }
    
    if ((node->flag & FLAG_READ) == 0) {
        pthread_mutex_unlock(&fs_mutex);
        return -EACCES;
    }
    
    if (offset < 0) {
        pthread_mutex_unlock(&fs_mutex);
        return -EINVAL;
    }
    
    if ((size_t)offset > node->size) {
        pthread_mutex_unlock(&fs_mutex);
        return 0;
    }
    
    size_t remaining = node->size - offset;
    if (size > remaining) {
        size = remaining;
    }
    
    if (size > 0) {
        memcpy(buf, node->content + offset, size);
    }
    
    pthread_mutex_unlock(&fs_mutex);
    return size;
}

int fusemod_write(const char *path, const char *buf, size_t size, off_t offset,
                         struct fuse_file_info *fi) {
    (void) fi;
    pthread_mutex_lock(&fs_mutex);
    node_t *node = find_node(path);
    
    if (node == NULL) {
        pthread_mutex_unlock(&fs_mutex);
        return -ENOENT;
    }

    if (node->type == TYPE_DIR) {
        pthread_mutex_unlock(&fs_mutex);
        return -EISDIR;
    }

    if ((node->flag & FLAG_WRITE) == 0) {
        pthread_mutex_unlock(&fs_mutex);
        return -EACCES;
    }
    
    if (offset < 0) {
        pthread_mutex_unlock(&fs_mutex);
        return -EINVAL;
    }

    // 调用 write_node_content 处理内存调整与写入

    if (node->flag & FLAG_COPY_ON_WRITE){
        int wres = write_node_content(node, buf, size, offset);
        if (wres != 0) {
            pthread_mutex_unlock(&fs_mutex);
            if (wres == ERR_IO_ERROR) return -ENOMEM;
            if (wres == ERR_INVALID_OPERATION) return -EACCES;
            return -EIO;
        }
    }

    // 准备通知并分片发送
    uint16_t path_len = strlen(path);
    size_t sent = 0;

    pthread_mutex_unlock(&fs_mutex);

    // 计算固定开销：PACKET_MIN_SIZE + 2 path_len字段 + path_len + 2 content_len + 4 offset
    size_t fixed_overhead = PACKET_MIN_SIZE + 2 + (size_t)path_len + 2 + 4; // = 14 + path_len + PACKET_MIN_SIZE
    if (fixed_overhead >= PACKET_MAX_SIZE) {
        // 无法发送任何内容
        return -EIO;
    }
    size_t max_chunk = PACKET_MAX_SIZE - fixed_overhead;

    while (sent < size) {
        size_t chunk = (size - sent) > max_chunk ? max_chunk : (size - sent);
        uint32_t data_size_chunk = 2 + path_len + 2 + (uint32_t)chunk + 4; // path_len(2) + path + content_len(2) + content + offset(4)
        size_t alloc_size = data_size_chunk + PACKET_MIN_SIZE;
        uint8_t *notification = malloc(alloc_size);
        if (notification == NULL) {
            return -ENOMEM;
        }

        // 在 notification+6 开始布局
        // path_len
        notification[6] = path_len & 0xFF;
        notification[7] = (path_len >> 8) & 0xFF;
        // path
        memcpy(notification + 8, path, path_len);
        // content_len
        uint32_t content_len_pos = 8 + path_len;
        notification[content_len_pos] = (chunk) & 0xFF;
        notification[content_len_pos + 1] = ((chunk) >> 8) & 0xFF;
        // content
        memcpy(notification + content_len_pos + 2, buf + sent, chunk);
        // offset (absolute)
        uint32_t off = (uint32_t)(offset + sent);
        size_t off_pos = content_len_pos + 2 + chunk;
        notification[off_pos] = off & 0xFF;
        notification[off_pos + 1] = (off >> 8) & 0xFF;
        notification[off_pos + 2] = (off >> 16) & 0xFF;
        notification[off_pos + 3] = (off >> 24) & 0xFF;

        size_t packet_size = create_response_packet(notification, 7, data_size_chunk, notification + 6);

        // 确保 packet_size 不超过 PACKET_MAX_SIZE
        if (packet_size > PACKET_MAX_SIZE) {
            free(notification);
            return -EIO;
        }

        ssize_t w = write(pipe_out_fd, notification, packet_size);
        free(notification);
        if (w < 0) {
            return -EIO;
        }

        sent += chunk;
    }

    return size;
}