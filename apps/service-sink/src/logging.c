#include "logging.h"
#include "log_capture.h"

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
    
    // Get container ID from hostname (pod name in Kubernetes)
    const char* container_id = getenv("HOSTNAME");
    if (!container_id) {
        container_id = "unknown";
    }
    
    // Try to get a more meaningful container name
    const char* container_name = getenv("CONTAINER_NAME");
    if (!container_name) {
        container_name = getenv("POD_NAME");  // In K8s, this is often more meaningful
    }
    if (!container_name) {
        container_name = container_id;  // Fallback to hostname
    }
    
    // Create JSON payload with container name
    snprintf(json_payload, sizeof(json_payload),
        "{"
        "\"service\":\"service-sink\","
        "\"level\":\"%s\","
        "\"message\":\"%s\","
        "\"metadata\":{\"timestamp\":\"%ld\",\"container_id\":\"%s\",\"container_name\":\"%s\"}"
        "}",
        level, message, time(NULL), container_id, container_name);
    
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
            LOG_ERROR("Failed to send log to logthon: %s", curl_easy_strerror(res));
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
        LOG_INFO("Service Sink request logged to: %s", filename);
        
        // Also log to console for immediate visibility
        LOG_INFO("  Query Params: %s", strlen(query_params) > 0 ? query_params : "(none)");
        if (req->body_length > 0) {
            LOG_INFO("  POST Body: %.*s", req->body_length, req->body);
        }
    } else {
        LOG_ERROR("Failed to open file for logging: %s", strerror(errno));
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
