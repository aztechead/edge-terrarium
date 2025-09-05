#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>
#include <errno.h>

#define PORT 8080
#define MAX_REQUEST_SIZE 1048576  // 1MB max request size

typedef struct {
    char method[16];
    char path[256];
    char version[16];
    char headers[4096];
    char body[MAX_REQUEST_SIZE];
    int body_length;
} http_request_t;

int parse_http_request(const char* request, http_request_t* req) {
    char* line_end;
    char* request_line = strtok_r((char*)request, "\r\n", &line_end);
    
    if (!request_line) return -1;
    
    // Parse request line: METHOD PATH VERSION
    if (sscanf(request_line, "%15s %255s %15s", req->method, req->path, req->version) != 3) {
        return -1;
    }
    
    // Parse headers
    char* header_line;
    char* header_end;
    req->headers[0] = '\0';
    
    while ((header_line = strtok_r(NULL, "\r\n", &line_end)) != NULL) {
        if (strlen(header_line) == 0) break; // Empty line indicates end of headers
        
        if (strlen(req->headers) + strlen(header_line) + 2 < sizeof(req->headers)) {
            strcat(req->headers, header_line);
            strcat(req->headers, "\n");
        }
    }
    
    // Get body if present
    req->body_length = 0;
    if (line_end && strlen(line_end) > 0) {
        req->body_length = strlen(line_end);
        if (req->body_length >= MAX_REQUEST_SIZE) {
            req->body_length = MAX_REQUEST_SIZE - 1;
        }
        memcpy(req->body, line_end, req->body_length);
        req->body[req->body_length] = '\0';
    }
    
    return 0;
}

void send_http_response(int client_socket, int status_code, const char* message) {
    char response[1024];
    snprintf(response, sizeof(response),
        "HTTP/1.1 %d %s\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n"
        "\r\n"
        "{\"status\":\"success\",\"message\":\"%s\",\"timestamp\":%ld,\"service\":\"service-sink\"}",
        status_code, message, strlen(message) + 80, message, time(0));
    
    send(client_socket, response, strlen(response), 0);
}

void handle_client(int client_socket, const char* client_ip) {
    char buffer[MAX_REQUEST_SIZE];
    int bytes_received = recv(client_socket, buffer, sizeof(buffer) - 1, 0);
    
    if (bytes_received <= 0) {
        close(client_socket);
        return;
    }
    
    buffer[bytes_received] = '\0';
    
    http_request_t req;
    if (parse_http_request(buffer, &req) == 0) {
        printf("Service Sink received %s request to %s from %s\n", req.method, req.path, client_ip);
        
        // Log request details
        printf("  Method: %s\n", req.method);
        printf("  Path: %s\n", req.path);
        printf("  Version: %s\n", req.version);
        printf("  Body Length: %d\n", req.body_length);
        
        // Simple request processing - count characters in path
        int path_length = strlen(req.path);
        char response_message[256];
        snprintf(response_message, sizeof(response_message), 
                "Service Sink processed request to path '%s' (length: %d)", 
                req.path, path_length);
        
        send_http_response(client_socket, 200, response_message);
    } else {
        printf("Failed to parse request from %s\n", client_ip);
        send_http_response(client_socket, 400, "Bad Request - Service Sink");
    }
    
    close(client_socket);
}

int main() {
    printf("Service Sink starting...\n");
    
    int server_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (server_socket < 0) {
        perror("Socket creation failed");
        return 1;
    }
    
    int opt = 1;
    if (setsockopt(server_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        perror("setsockopt failed");
        close(server_socket);
        return 1;
    }
    
    struct sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(PORT);
    
    if (bind(server_socket, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        perror("Bind failed");
        close(server_socket);
        return 1;
    }
    
    if (listen(server_socket, 10) < 0) {
        perror("Listen failed");
        close(server_socket);
        return 1;
    }
    
    printf("Service Sink listening on port %d\n", PORT);
    
    while (1) {
        struct sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);
        int client_socket = accept(server_socket, (struct sockaddr*)&client_addr, &client_len);
        
        if (client_socket < 0) {
            perror("Accept failed");
            continue;
        }
        
        char client_ip[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &client_addr.sin_addr, client_ip, INET_ADDRSTRLEN);
        
        // Handle client in main thread for simplicity
        handle_client(client_socket, client_ip);
    }
    
    close(server_socket);
    return 0;
}
