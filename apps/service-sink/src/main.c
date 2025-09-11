#include "common.h"
#include "logging.h"
#include "http_server.h"
#include "log_capture.h"

int main() {
    // Initialize log capture system first
    init_log_capture();
    
    printf("Service Sink starting...\n");
    fflush(stdout);
    
    // Create request directory
    printf("Creating request directory...\n");
    fflush(stdout);
    if (mkdir("/tmp/requests", 0755) != 0 && errno != EEXIST) {
        perror("Failed to create requests directory");
        return 1;
    }
    
    // Initialize curl
    printf("Initializing curl...\n");
    fflush(stdout);
    curl_global_init(CURL_GLOBAL_DEFAULT);
    
    // Send startup log after curl is initialized with a small delay
    printf("Waiting for logthon to be ready...\n");
    fflush(stdout);
    sleep(2);  // Give logthon a moment to be fully ready
    printf("Sending startup log to logthon...\n");
    fflush(stdout);
    send_log_to_logthon("INFO", "Service Sink service starting up");
    printf("Startup log sent successfully\n");
    fflush(stdout);
    
    int server_socket = create_server_socket(PORT);
    if (server_socket < 0) {
        perror("Failed to create server socket");
        curl_global_cleanup();
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
    
    // Cleanup
    cleanup_log_capture();
    curl_global_cleanup();
    
    return 0;
}
