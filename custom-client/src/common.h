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
#include <sys/select.h>
#include <pthread.h>
#include <curl/curl.h>
#include <json-c/json.h>

// Function declarations
size_t write_callback(void* contents, size_t size, size_t nmemb, void* userp);

// Constants
#define BUFFER_SIZE 5242880  // 5MB buffer
#define MAX_REQUEST_SIZE 1048576  // 1MB max request size
#define PORT_HTTP 1337
#define DEFAULT_VAULT_ADDR "http://vault.edge-terrarium.svc.cluster.local:8200"
#define DEFAULT_VAULT_TOKEN "root"
#define MAX_SECRET_SIZE 4096
#define DEFAULT_FILE_STORAGE_URL "http://file-storage-service.edge-terrarium.svc.cluster.local:9000"

// HTTP Request structure
typedef struct {
    char method[16];
    char path[256];
    char version[16];
    char headers[4096];
    char body[MAX_REQUEST_SIZE];
    int body_length;
} http_request_t;

// Vault secrets structure
typedef struct {
    char api_key[256];
    char database_url[512];
    char jwt_secret[256];
    char encryption_key[256];
    char log_level[64];
    char max_connections[64];
} vault_secrets_t;

#endif // COMMON_H
