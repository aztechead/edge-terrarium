#include "common.h"
#include "vault.h"
#include "file_storage.h"
#include "logging.h"
#include "http_server.h"
#include "log_capture.h"

int main() {
    // Initialize log capture system first
    init_log_capture();
    
    send_log_to_logthon("INFO", "Custom Client service starting up");
    
    // Initialize curl
    curl_global_init(CURL_GLOBAL_DEFAULT);
    
    // Retrieve secrets from Vault
    vault_secrets_t secrets;
    if (retrieve_vault_secrets(&secrets) == 0) {
        log_vault_secrets(&secrets);
    } else {
        LOG_WARN("Failed to retrieve secrets from Vault, continuing with default values");
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
    mkdir("/tmp/requests", 0755);
    int http_socket = create_server_socket(PORT_HTTP);
    
    if (http_socket < 0) {
        LOG_ERROR("Failed to create server socket");
        curl_global_cleanup();
        return 1;
    }
    
    LOG_INFO("Custom Client listening on port %d (HTTP)", PORT_HTTP);
    
    // Start the file creation thread
    pthread_t file_thread;
    if (pthread_create(&file_thread, NULL, file_creation_thread, NULL) != 0) {
        LOG_ERROR("Failed to create file creation thread");
    } else {
        LOG_INFO("File creation thread started successfully");
    }
    
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
    cleanup_log_capture();
    curl_global_cleanup();
    return 0;
}
