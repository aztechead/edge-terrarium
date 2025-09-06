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
    char* request_copy = strdup(request);
    if (!request_copy) return -1;
    
    // Find the end of headers (double CRLF)
    char* header_end = strstr(request_copy, "\r\n\r\n");
    if (!header_end) {
        // Try single CRLF
        header_end = strstr(request_copy, "\n\n");
        if (!header_end) {
            free(request_copy);
            return -1;
        }
        header_end += 2; // Skip \n\n
    } else {
        header_end += 4; // Skip \r\n\r\n
    }
    
    // Parse request line and headers
    char* headers_section = request_copy;
    *header_end = '\0'; // Null terminate headers section
    
    char* line_end;
    char* request_line = strtok_r(headers_section, "\r\n", &line_end);
    
    if (!request_line) {
        free(request_copy);
        return -1;
    }
    
    // Parse request line: METHOD PATH VERSION
    if (sscanf(request_line, "%15s %255s %15s", req->method, req->path, req->version) != 3) {
        free(request_copy);
        return -1;
    }
    
    // Parse headers
    char* header_line;
    req->headers[0] = '\0';
    
    while ((header_line = strtok_r(NULL, "\r\n", &line_end)) != NULL) {
        if (strlen(header_line) == 0) break; // Empty line indicates end of headers
        
        if (strlen(req->headers) + strlen(header_line) + 2 < sizeof(req->headers)) {
            strcat(req->headers, header_line);
            strcat(req->headers, "\n");
        }
    }
    
    // Get body if present (everything after the header section)
    req->body_length = 0;
    if (*header_end != '\0') {
        // Skip any leading whitespace/newlines
        while (*header_end == '\r' || *header_end == '\n' || *header_end == ' ') {
            header_end++;
        }
        
        if (*header_end != '\0') {
            req->body_length = strlen(header_end);
            if (req->body_length >= MAX_REQUEST_SIZE) {
                req->body_length = MAX_REQUEST_SIZE - 1;
            }
            memcpy(req->body, header_end, req->body_length);
            req->body[req->body_length] = '\0';
        }
    }
    
    free(request_copy);
    return 0;
}

// Function to extract query parameters from path
void extract_query_params(const char* path, char* query_params, size_t query_params_size) {
    const char* query_start = strchr(path, '?');
    if (query_start) {
        query_start++; // Skip the '?'
        size_t query_len = strlen(query_start);
        if (query_len < query_params_size) {
            strncpy(query_params, query_start, query_params_size - 1);
            query_params[query_params_size - 1] = '\0';
        }
    } else {
        query_params[0] = '\0';
    }
}

// Function to send log to logthon
void send_log_to_logthon(const char* level, const char* message) {
    CURL *curl;
    CURLcode res;
    char logthon_url[256];
    char json_payload[2048];
    
    // Get logthon URL from environment or use default
    const char* logthon_host = getenv("LOGTHON_HOST");
    if (!logthon_host) {
        logthon_host = "logthon";
    }
    const char* logthon_port = getenv("LOGTHON_PORT");
    if (!logthon_port) {
        logthon_port = "5000";
    }
    
    snprintf(logthon_url, sizeof(logthon_url), "http://%s:%s/api/logs", logthon_host, logthon_port);
    
    // Create JSON payload
    snprintf(json_payload, sizeof(json_payload),
        "{"
        "\"service\":\"service-sink\","
        "\"level\":\"%s\","
        "\"message\":\"%s\","
        "\"metadata\":{\"timestamp\":\"%ld\"}"
        "}",
        level, message, time(NULL));
    
    curl = curl_easy_init();
    if (curl) {
        struct curl_slist *headers = NULL;
        headers = curl_slist_append(headers, "Content-Type: application/json");
        
        curl_easy_setopt(curl, CURLOPT_URL, logthon_url);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json_payload);
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 2L); // 2 second timeout
        curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 1L); // 1 second connect timeout
        
        // Perform the request
        res = curl_easy_perform(curl);
        
        // Cleanup
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);
        
        if (res != CURLE_OK) {
            printf("Failed to send log to logthon: %s\n", curl_easy_strerror(res));
        }
    }
}

void log_request(const http_request_t* req, const char* client_ip) {
    time_t now = time(0);
    char timestamp[64];
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", localtime(&now));
    
    // Create filename with timestamp
    char filename[128];
    snprintf(filename, sizeof(filename), "/tmp/requests/service-sink-request_%ld_%s.txt", now, client_ip);
    
    // Ensure directory exists
    mkdir("/tmp/requests", 0755);
    
    // Extract query parameters
    char query_params[512] = {0};
    extract_query_params(req->path, query_params, sizeof(query_params));
    
    FILE* file = fopen(filename, "w");
    if (file) {
        fprintf(file, "=== Service Sink HTTP Request Log ===\n");
        fprintf(file, "Timestamp: %s\n", timestamp);
        fprintf(file, "Client IP: %s\n", client_ip);
        fprintf(file, "Method: %s\n", req->method);
        fprintf(file, "Path: %s\n", req->path);
        fprintf(file, "Version: %s\n", req->version);
        fprintf(file, "Headers:\n%s\n", req->headers);
        
        // Log query parameters if present
        if (strlen(query_params) > 0) {
            fprintf(file, "Query Parameters: %s\n", query_params);
        } else {
            fprintf(file, "Query Parameters: (none)\n");
        }
        
        fprintf(file, "Body Length: %d\n", req->body_length);
        if (req->body_length > 0) {
            fprintf(file, "Body Content:\n%.*s\n", req->body_length, req->body);
        } else {
            fprintf(file, "Body Content: (empty)\n");
        }
        fprintf(file, "=== End Request ===\n");
        fclose(file);
        printf("Service Sink request logged to: %s\n", filename);
        
        // Also log to console for immediate visibility
        printf("  Query Params: %s\n", strlen(query_params) > 0 ? query_params : "(none)");
        if (req->body_length > 0) {
            printf("  POST Body: %.*s\n", req->body_length, req->body);
        }
    } else {
        printf("Failed to open file for logging: %s\n", strerror(errno));
    }
    
    // Send log to logthon
    char log_message[1024];
    snprintf(log_message, sizeof(log_message), 
        "Request: %s %s from %s (Query: %s, Body: %d bytes)", 
        req->method, req->path, client_ip,
        strlen(query_params) > 0 ? query_params : "none",
        req->body_length);
    send_log_to_logthon("INFO", log_message);
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
        
        // Log request to file and console
        log_request(&req, client_ip);
        
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
    send_log_to_logthon("INFO", "Service Sink service starting up");
    
    // Create request directory
    printf("Creating request directory...\n");
    mkdir("/tmp/requests", 0755);
    
    // Initialize curl
    printf("Initializing curl...\n");
    curl_global_init(CURL_GLOBAL_DEFAULT);
    
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
    
    // Cleanup curl
    curl_global_cleanup();
    
    return 0;
}
