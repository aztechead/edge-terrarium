#include "http_server.h"
#include "logging.h"
#include "log_capture.h"

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
    char* body_start = header_end; // Save pointer to body before null-terminating
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
    if (*body_start != '\0') {
        // Skip any leading whitespace/newlines
        while (*body_start == '\r' || *body_start == '\n' || *body_start == ' ') {
            body_start++;
        }
        
        if (*body_start != '\0') {
            req->body_length = strlen(body_start);
            if (req->body_length >= MAX_REQUEST_SIZE) {
                req->body_length = MAX_REQUEST_SIZE - 1;
            }
            memcpy(req->body, body_start, req->body_length);
            req->body[req->body_length] = '\0';
        }
    }
    
    free(request_copy);
    return 0;
}

void send_http_response(int client_socket, int status_code, const char* message) {
    char response[1024];
    char json_body[512];
    
    // Create the JSON body first to calculate its actual length
    snprintf(json_body, sizeof(json_body),
        "{\"status\":\"success\",\"message\":\"%s\",\"timestamp\":%ld,\"service\":\"service-sink\"}",
        message, time(0));
    
    snprintf(response, sizeof(response),
        "HTTP/1.1 %d %s\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n"
        "\r\n"
        "%s",
        status_code, message, strlen(json_body), json_body);
    
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
        // Check if this is a health check request first
        if (strcmp(req.path, "/health") == 0) {
            // Check for probe type header to identify liveness vs readiness
            char probe_type[32] = "unknown";
            if (strstr(req.headers, "X-Probe-Type: liveness") != NULL) {
                strcpy(probe_type, "liveness");
            } else if (strstr(req.headers, "X-Probe-Type: readiness") != NULL) {
                strcpy(probe_type, "readiness");
            }
            
            LOG_INFO("Service Sink %s probe from %s", probe_type, client_ip);
            
            // Send detailed health check log to logthon (skip general request logging)
            char health_log_message[512];
            snprintf(health_log_message, sizeof(health_log_message), 
                    "Health check: %s probe from %s", probe_type, client_ip);
            send_log_to_logthon("INFO", health_log_message);
            
            send_http_response(client_socket, 200, "Service Sink is healthy");
        } else {
            // For non-health check requests, do normal logging
            LOG_INFO("Service Sink received %s request to %s from %s", req.method, req.path, client_ip);
            log_request(&req, client_ip);
            
            // Simple request processing - count characters in path
            int path_length = strlen(req.path);
            char response_message[256];
            snprintf(response_message, sizeof(response_message), 
                    "Service Sink processed request to path '%s' (length: %d)", 
                    req.path, path_length);
            
            send_http_response(client_socket, 200, response_message);
        }
    } else {
        LOG_ERROR("Failed to parse request from %s", client_ip);
        send_http_response(client_socket, 400, "Bad Request - Service Sink");
    }
    
    close(client_socket);
}

int create_server_socket(int port) {
    int server_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (server_socket < 0) {
        perror("Socket creation failed");
        return -1;
    }
    
    int opt = 1;
    if (setsockopt(server_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        perror("setsockopt failed");
        close(server_socket);
        return -1;
    }
    
    struct sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(port);
    
    if (bind(server_socket, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        perror("Bind failed");
        close(server_socket);
        return -1;
    }
    
    if (listen(server_socket, 10) < 0) {
        perror("Listen failed");
        close(server_socket);
        return -1;
    }
    
    return server_socket;
}
