#include "fuseMod.h"

// 递归删除目录
void delete_directory_recursive(node_t *dir) {
    node_t *child = dir->children;
    while (child != NULL) {
        node_t *next = child->next;
        
        if (child->type == TYPE_DIR) {
            delete_directory_recursive(child);
        } else {
            free(child->name);
            free(child->content);
            free(child);
        }
        
        child = next;
    }
    
    free(dir->name);
    free(dir);
}

// 查找节点
node_t *find_node(const char *path) {
    if (strcmp(path, "/") == 0) {
        return root;
    }
    
    char **components = NULL;
    int count = split_path(path, &components);
    if (count <= 0) {
        return NULL;
    }
    
    node_t *current = root;
    for (int i = 0; i < count; i++) {
        node_t *child = current->children;
        node_t *found = NULL;
        
        while (child != NULL) {
            if (strcmp(child->name, components[i]) == 0) {
                found = child;
                break;
            }
            child = child->next;
        }
        
        if (found == NULL) {
            for (int j = 0; j < count; j++) {
                free(components[j]);
            }
            free(components);
            return NULL;
        }
        
        current = found;
    }
    
    for (int i = 0; i < count; i++) {
        free(components[i]);
    }
    free(components);
    
    return current;
}

// 创建目录
int create_directory(const char *path) {
    if (path == NULL || path[0] != '/') {
        return ERR_INVALID_PATH;
    }
    
    if (strcmp(path, "/") == 0) {
        return ERR_ALREADY_EXISTS;
    }
    
    // 检查是否已存在
    if (find_node(path) != NULL) {
        return ERR_ALREADY_EXISTS;
    }
    
    // 查找父目录
    char *parent_path = strdup(path);
    if (parent_path == NULL) {
        return ERR_IO_ERROR;
    }
    
    char *last_slash = strrchr(parent_path, '/');

    if (last_slash == NULL) {
        free(parent_path);
        return ERR_INVALID_PATH;
    }
    
    if (last_slash == parent_path) {
        // 父目录是根目录
        *(last_slash + 1) = '\0';
    } else {
        *last_slash = '\0';
    }
    
    node_t *parent = find_node(parent_path);
    if (parent == NULL) {
        free(parent_path);
        return ERR_NOT_FOUND;
    }
    
    free(parent_path);
    
    // 创建新目录
    node_t *new_dir = malloc(sizeof(node_t));
    if (new_dir == NULL) {
        return ERR_IO_ERROR;
    }
    
    char *name = strrchr(path, '/') + 1;
    new_dir->name = strdup(name);
    new_dir->type = TYPE_DIR;
    new_dir->mode = S_IFDIR | 0755;
    new_dir->uid = getuid();
    new_dir->gid = getgid();
    new_dir->content = NULL;
    new_dir->size = 0;
    new_dir->mtime = time(NULL);
    new_dir->parent = parent;
    new_dir->children = NULL;
    new_dir->next = parent->children;
    parent->children = new_dir;
    
    return 0;
}

// 创建文件
int create_file(const char *path, uint32_t flag) {
    if (path == NULL || path[0] != '/') {
        return ERR_INVALID_PATH;
    }
    // 检查是否已存在
    if (find_node(path) != NULL) {
        return ERR_ALREADY_EXISTS;
    }
    // 查找父目录
    char *parent_path = strdup(path);
    if (parent_path == NULL) {
        return ERR_IO_ERROR;
    }
    char *last_slash = strrchr(parent_path, '/');
    if (last_slash == NULL) {
        free(parent_path);
        return ERR_INVALID_PATH;
    }

    if (last_slash == parent_path) {
        // 父目录是根目录
        *(last_slash + 1) = '\0';
    } else {
        *last_slash = '\0';
    }
    // *(last_slash + 1) = '\0';

    node_t *parent = find_node(parent_path);
    if (parent == NULL) {
        free(parent_path);
        return ERR_NOT_FOUND;
    }
    
    free(parent_path);
    
    // 创建新文件
    node_t *new_file = malloc(sizeof(node_t));
    if (new_file == NULL) {
        return ERR_IO_ERROR;
    }
    
    char *name = strrchr(path, '/') + 1;
    new_file->name = strdup(name);
    new_file->type = TYPE_FILE;

    if ((flag & FLAG_READ) && (flag & FLAG_WRITE)) {
        new_file->mode = S_IFREG | 0666;
    } 
    else if (flag & FLAG_READ) {
        new_file->mode = S_IFREG | 0444;
    } 
    else if (flag & FLAG_WRITE) {
        new_file->mode = S_IFREG | 0222;
    } 
    else {
        new_file->mode = S_IFREG | 0000;
    }

    new_file->uid = getuid();
    new_file->gid = getgid();
    new_file->content = NULL;
    new_file->size = 0;
    new_file->flag = flag;
    new_file->mtime = time(NULL);
    new_file->parent = parent;
    new_file->children = NULL;
    new_file->next = parent->children;
    parent->children = new_file;
    
    return 0;
}

// 删除目录
int delete_directory(const char *path) {
    if (path == NULL || path[0] != '/') {
        return ERR_INVALID_PATH;
    }
    
    if (strcmp(path, "/") == 0) {
        return ERR_INVALID_OPERATION; // 不能删除根目录
    }
    
    node_t *dir = find_node(path);
    if (dir == NULL) {
        return ERR_NOT_FOUND;
    }
    
    if (dir->type != TYPE_DIR) {
        return ERR_INVALID_OPERATION;
    }
    
    // 从父目录中移除
    node_t *parent = dir->parent;
    node_t *prev = NULL;
    node_t *curr = parent->children;
    
    while (curr != NULL) {
        if (curr == dir) {
            if (prev == NULL) {
                parent->children = curr->next;
            } else {
                prev->next = curr->next;
            }
            break;
        }
        prev = curr;
        curr = curr->next;
    }
    
    // 递归删除
    delete_directory_recursive(dir);
    
    return 0;
}

// 删除文件
int delete_file(const char *path) {
    if (path == NULL || path[0] != '/') {
        return ERR_INVALID_PATH;
    }
    
    node_t *file = find_node(path);
    if (file == NULL) {
        return ERR_NOT_FOUND;
    }
    
    if (file->type == TYPE_DIR) {
        return ERR_INVALID_OPERATION;
    }
    
    // 从父目录中移除
    node_t *parent = file->parent;
    node_t *prev = NULL;
    node_t *curr = parent->children;
    
    while (curr != NULL) {
        if (curr == file) {
            if (prev == NULL) {
                parent->children = curr->next;
            } else {
                prev->next = curr->next;
            }
            break;
        }
        prev = curr;
        curr = curr->next;
    }
    
    free(file->name);
    free(file->content);
    free(file);
    
    return 0;
}

// 设置文件内容
int set_file_content(const char *path, const uint8_t *content, size_t content_size) {
    node_t *file = find_node(path);
    if (file == NULL) {
        return ERR_NOT_FOUND;
    }
    
    if (file->type == TYPE_DIR) {
        return ERR_INVALID_OPERATION;
    }

    if ((file->flag & FLAG_READ) == 0) {
        return ERR_INVALID_OPERATION;
    }
    
    free(file->content);
    
    if (content_size > 0) {
        file->content = malloc(content_size);
        if (file->content == NULL) {
            file->size = 0;
            return ERR_IO_ERROR;
        }
        memcpy(file->content, content, content_size);
    } else {
        file->content = NULL;
    }
    
    file->size = content_size;
    file->mtime = time(NULL);
    
    return 0;
}

// 追加文件内容
int append_file_content(const char *path, const uint8_t *content, size_t content_size) {
    node_t *file = find_node(path);
    if (file == NULL) {
        return ERR_NOT_FOUND;
    }
    
    if (file->type == TYPE_DIR) {
        return ERR_INVALID_OPERATION;
    }

    if ((file->flag & FLAG_READ) == 0) {
        return ERR_INVALID_OPERATION;
    }
    
    size_t new_size = file->size + content_size;
    char *new_content = realloc(file->content, new_size);
    if (new_content == NULL && new_size > 0) {
        return ERR_IO_ERROR;
    }
    
    if (content_size > 0) {
        memcpy(new_content + file->size, content, content_size);
    }
    
    file->content = new_content;
    file->size = new_size;
    file->mtime = time(NULL);
    
    return 0;
}

// 写入节点内容（在 caller 持有 fs_mutex 时调用）
int write_node_content(node_t *node, const char *buf, size_t size, off_t offset) {
    if (node == NULL) {
        return ERR_NOT_FOUND;
    }

    if (node->type == TYPE_DIR) {
        return ERR_INVALID_OPERATION;
    }

    if ((node->flag & FLAG_WRITE) == 0) {
        return ERR_INVALID_OPERATION;
    }

    if (offset < 0) {
        return ERR_INVALID_OPERATION;
    }

    // 调整文件内容大小
    if ((size_t)offset + size > node->size) {
        char *new_content = realloc(node->content, offset + size);
        if (new_content == NULL) {
            return ERR_IO_ERROR;
        }

        if ((size_t)offset > node->size) {
            memset(new_content + node->size, 0, offset - node->size);
        }

        node->content = new_content;
        node->size = offset + size;
    }

    if (size > 0) {
        memcpy(node->content + offset, buf, size);
    }

    node->mtime = time(NULL);
    return 0;
}

// 初始化文件系统
void init_filesystem() {
    root = malloc(sizeof(node_t));
    if (root == NULL) {
        send_error_and_exit(0, "init_filesystem err");
    }
    
    root->name = strdup("");
    root->type = TYPE_DIR;
    root->mode = S_IFDIR | 0755;
    root->uid = getuid();
    root->gid = getgid();
    root->content = NULL;
    root->size = 0;
    root->mtime = time(NULL);
    root->parent = NULL;
    root->children = NULL;
    root->next = NULL;
}