CC = gcc
CFLAGS = -IfuseMod_src -Wall -D_FILE_OFFSET_BITS=64 -DFUSE_USE_VERSION=31
LIBS = -lfuse3 -lpthread

all:
	$(CC) $(CFLAGS) -o fuseMod fuseMod_src/fuseMod_main.c fuseMod_src/fuseMod_pipe.c fuseMod_src/fuseMod_file.c fuseMod_src/fuseMod_tools.c fuseMod_src/fuseMod_fuse.c $(LIBS)
