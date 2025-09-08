#include "common.h"
#include "vault.h"
#include "file_storage.h"
#include "logging.h"
#include "http_server.h"
#include "log_capture.h"

int main() {
    // Initialize log capture system first
    init_log_capture();
    
    printf("Custom Client starting...\n");
    send_log_to_logthon("INFO", "Custom Client service starting up");
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
        curl_global_cleanup();
        return 1;
    }
    
    printf("Custom Client listening on port %d (HTTP)\n", PORT_HTTP);
    fflush(stdout);
    
    // Start the file creation thread
    pthread_t file_thread;
    if (pthread_create(&file_thread, NULL, file_creation_thread, NULL) != 0) {
        printf("Failed to create file creation thread\n");
        fflush(stdout);
    } else {
        printf("File creation thread started successfully\n");
        fflush(stdout);
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
