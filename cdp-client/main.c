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
#include <curl/curl.h>
#include <json-c/json.h>

#define BUFFER_SIZE 5242880  // 5MB buffer
#define MAX_REQUEST_SIZE 1048576  // 1MB max request size
#define PORT_HTTP 1337
#define DEFAULT_VAULT_ADDR "http://vault.terrarium.svc.cluster.local:8200"
#define DEFAULT_VAULT_TOKEN "root"
#define MAX_SECRET_SIZE 4096

typedef struct {
    char method[16];
    char path[256];
    char version[16];
    char headers[4096];
    char body[MAX_REQUEST_SIZE];
    int body_length;
} http_request_t;

// Structure to hold Vault secrets
typedef struct {
    char api_key[256];
    char database_url[512];
    char jwt_secret[256];
    char encryption_key[256];
    char log_level[64];
    char max_connections[64];
} vault_secrets_t;

// Callback function for curl to write response data
size_t write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t realsize = size * nmemb;
    char* response = (char*)userp;
    strncat(response, (char*)contents, realsize);
    return realsize;
}

// Function to retrieve a secret from Vault
int get_vault_secret(const char* secret_path, const char* key, char* output, size_t output_size) {
    CURL* curl;
    CURLcode res;
    char url[512];
    char response[MAX_SECRET_SIZE] = {0};
    char auth_header[256];
    char* vault_addr;
    char* vault_token;
    
    // Get Vault configuration from environment variables
    vault_addr = getenv("VAULT_ADDR");
    if (!vault_addr) {
        vault_addr = (char*)DEFAULT_VAULT_ADDR;
    }
    
    vault_token = getenv("VAULT_TOKEN");
    if (!vault_token) {
        vault_token = (char*)DEFAULT_VAULT_TOKEN;
    }
    
    // Initialize curl
    curl = curl_easy_init();
    if (!curl) {
        printf("Failed to initialize curl\n");
        return -1;
    }
    
    // Build the Vault API URL
    snprintf(url, sizeof(url), "%s/v1/secret/data/%s", vault_addr, secret_path);
    
    // Build the authorization header
    snprintf(auth_header, sizeof(auth_header), "X-Vault-Token: %s", vault_token);
    
    // Set curl options
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, response);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, curl_slist_append(NULL, auth_header));
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10L);
    
    // Perform the request
    res = curl_easy_perform(curl);
    
    if (res != CURLE_OK) {
        printf("curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
        curl_easy_cleanup(curl);
        return -1;
    }
    
    
    // Parse the JSON response
    json_object* json = json_tokener_parse(response);
    if (!json) {
        printf("Failed to parse JSON response from Vault\n");
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Navigate to the secret value
    json_object* data_obj;
    json_object* data_data_obj;
    json_object* key_obj;
    
    if (json_object_object_get_ex(json, "data", &data_obj) &&
        json_object_object_get_ex(data_obj, "data", &data_data_obj) &&
        json_object_object_get_ex(data_data_obj, key, &key_obj)) {
        
        const char* value = json_object_get_string(key_obj);
        if (value) {
            strncpy(output, value, output_size - 1);
            output[output_size - 1] = '\0';
        } else {
            printf("Failed to get string value for key: %s\n", key);
            json_object_put(json);
            curl_easy_cleanup(curl);
            return -1;
        }
    } else {
        printf("Failed to find key '%s' in Vault response\n", key);
        json_object_put(json);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Cleanup
    json_object_put(json);
    curl_easy_cleanup(curl);
    return 0;
}

// Function to retrieve all secrets from Vault
int retrieve_vault_secrets(vault_secrets_t* secrets) {
    printf("Retrieving secrets from Vault...\n");
    
    int success = 1;
    
    // Retrieve configuration secrets
    if (get_vault_secret("cdp-client/config", "api_key", secrets->api_key, sizeof(secrets->api_key)) != 0) {
        printf("Failed to retrieve api_key from Vault\n");
        success = 0;
    }
    
    if (get_vault_secret("cdp-client/config", "database_url", secrets->database_url, sizeof(secrets->database_url)) != 0) {
        printf("Failed to retrieve database_url from Vault\n");
        success = 0;
    }
    
    if (get_vault_secret("cdp-client/config", "jwt_secret", secrets->jwt_secret, sizeof(secrets->jwt_secret)) != 0) {
        printf("Failed to retrieve jwt_secret from Vault\n");
        success = 0;
    }
    
    if (get_vault_secret("cdp-client/config", "encryption_key", secrets->encryption_key, sizeof(secrets->encryption_key)) != 0) {
        printf("Failed to retrieve encryption_key from Vault\n");
        success = 0;
    }
    
    if (get_vault_secret("cdp-client/config", "log_level", secrets->log_level, sizeof(secrets->log_level)) != 0) {
        printf("Failed to retrieve log_level from Vault\n");
        success = 0;
    }
    
    if (get_vault_secret("cdp-client/config", "max_connections", secrets->max_connections, sizeof(secrets->max_connections)) != 0) {
        printf("Failed to retrieve max_connections from Vault\n");
        success = 0;
    }
    
    if (success) {
        printf("Successfully retrieved all secrets from Vault\n");
    } else {
        printf("Some secrets could not be retrieved from Vault\n");
    }
    
    return success ? 0 : -1;
}

// Function to log retrieved secrets (for demonstration)
void log_vault_secrets(const vault_secrets_t* secrets) {
    printf("\n=== VAULT SECRETS RETRIEVED ===\n");
    printf("API Key: %s\n", secrets->api_key);
    printf("Database URL: %s\n", secrets->database_url);
    printf("JWT Secret: %s\n", secrets->jwt_secret);
    printf("Encryption Key: %s\n", secrets->encryption_key);
    printf("Log Level: %s\n", secrets->log_level);
    printf("Max Connections: %s\n", secrets->max_connections);
    printf("=== END VAULT SECRETS ===\n\n");
}

void log_request(const http_request_t* req, const char* client_ip) {
    time_t now = time(0);
    char timestamp[64];
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", localtime(&now));
    
    // Create filename with timestamp
    char filename[128];
    snprintf(filename, sizeof(filename), "/tmp/requests/request_%ld_%s.txt", now, client_ip);
    
    // Ensure directory exists
    mkdir("/tmp/requests", 0755);
    
    FILE* file = fopen(filename, "w");
    if (file) {
        fprintf(file, "=== HTTP Request Log ===\n");
        fprintf(file, "Timestamp: %s\n", timestamp);
        fprintf(file, "Client IP: %s\n", client_ip);
        fprintf(file, "Method: %s\n", req->method);
        fprintf(file, "Path: %s\n", req->path);
        fprintf(file, "Version: %s\n", req->version);
        fprintf(file, "Headers:\n%s\n", req->headers);
        fprintf(file, "Body Length: %d\n", req->body_length);
        if (req->body_length > 0) {
            fprintf(file, "Body:\n%.*s\n", req->body_length, req->body);
        }
        fprintf(file, "=== End Request ===\n");
        fclose(file);
        printf("Request logged to: %s\n", filename);
    } else {
        printf("Failed to open file for logging: %s\n", strerror(errno));
    }
}

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
        "{\"status\":\"success\",\"message\":\"%s\",\"timestamp\":%ld}",
        status_code, message, strlen(message) + 50, message, time(0));
    
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
        printf("Received %s request to %s from %s\n", req.method, req.path, client_ip);
        log_request(&req, client_ip);
        
        // Check if this is a route we should handle
        if (strstr(req.path, "/fake-provider/") || strstr(req.path, "/example-provider/")) {
            send_http_response(client_socket, 200, "CDP Client processed request successfully");
        } else {
            send_http_response(client_socket, 200, "CDP Client received request");
        }
    } else {
        printf("Failed to parse request from %s\n", client_ip);
        send_http_response(client_socket, 400, "Bad Request");
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

int main() {
    printf("CDP Client starting...\n");
    fflush(stdout);
    
    // Initialize curl
    printf("Initializing curl...\n");
    fflush(stdout);
    curl_global_init(CURL_GLOBAL_DEFAULT);
    printf("Curl initialized successfully\n");
    fflush(stdout);
    
    // Retrieve secrets from Vault
    printf("Retrieving secrets from Vault...\n");
    fflush(stdout);
    vault_secrets_t secrets;
    if (retrieve_vault_secrets(&secrets) == 0) {
        printf("Successfully retrieved secrets from Vault\n");
        fflush(stdout);
        log_vault_secrets(&secrets);
    } else {
        printf("Warning: Failed to retrieve secrets from Vault, continuing with default values\n");
        fflush(stdout);
        // Set default values if Vault is not available
        strcpy(secrets.api_key, "default-api-key");
        strcpy(secrets.database_url, "default-database-url");
        strcpy(secrets.jwt_secret, "default-jwt-secret");
        strcpy(secrets.encryption_key, "default-encryption-key");
        strcpy(secrets.log_level, "INFO");
        strcpy(secrets.max_connections, "100");
        log_vault_secrets(&secrets);
    }
    
    // Create request directory
    printf("Creating request directory...\n");
    fflush(stdout);
    mkdir("/tmp/requests", 0755);
    
    printf("Creating server socket...\n");
    fflush(stdout);
    int http_socket = create_server_socket(PORT_HTTP);
    
    if (http_socket < 0) {
        printf("Failed to create server socket\n");
        fflush(stdout);
        // curl_global_cleanup();
        return 1;
    }
    
    printf("CDP Client listening on port %d (HTTP)\n", PORT_HTTP);
    fflush(stdout);
    
    while (1) {
        struct sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);
        int client_socket = accept(http_socket, (struct sockaddr*)&client_addr, &client_len);
        
        if (client_socket < 0) {
            perror("Accept failed");
            continue;
        }
        
        char client_ip[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &client_addr.sin_addr, client_ip, INET_ADDRSTRLEN);
        handle_client(client_socket, client_ip);
    }
    
    close(http_socket);
    curl_global_cleanup();
    return 0;
}
