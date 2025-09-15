#ifndef COMMON_H
#define COMMON_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <curl/curl.h>
#include <json-c/json.h>

// Constants
#define PORT 8080
#define MAX_REQUEST_SIZE 1048576  // 1MB max request size

// HTTP Request structure
typedef struct {
    char method[16];
    char path[256];
    char version[16];
    char headers[4096];
    char body[MAX_REQUEST_SIZE];
    int body_length;
} http_request_t;

#endif // COMMON_H
