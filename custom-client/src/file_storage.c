#include "file_storage.h"
#include "logging.h"
#include "log_capture.h"

// Function to call the file storage API to create a new file
int create_file_via_api() {
    CURL* curl;
    CURLcode res;
    char url[512];
    char response[1024] = {0};
    char json_payload[2048];
    char timestamp[64];
    char* file_storage_url;
    time_t now;
    struct tm *tm_info;
    
    // Get current timestamp for filename
    time(&now);
    tm_info = localtime(&now);
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d_%H-%M-%S", tm_info);
    
    // Get file storage URL from environment variables
    file_storage_url = getenv("FILE_STORAGE_URL");
    if (!file_storage_url) {
        file_storage_url = (char*)DEFAULT_FILE_STORAGE_URL;
    }
    
    // Build the API URL
    snprintf(url, sizeof(url), "%s/files", file_storage_url);
    
    // Create JSON payload with filename and content
    snprintf(json_payload, sizeof(json_payload),
             "{\"filename_prefix\":\"%s\",\"content\":\"Custom Client generated file at %s\\n\\nThis is a test file created by the Custom Client application.\\n\\nFile Details:\\n- Created: %s\\n- Service: custom-client\\n- Purpose: Automated file creation test\\n\\nLorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.\\n\\nDuis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.\",\"extension\":\".txt\"}",
             timestamp, timestamp, timestamp);
    
    // Initialize curl
    curl = curl_easy_init();
    if (!curl) {
        LOG_ERROR("Failed to initialize curl for file storage API");
        return -1;
    }
    
    // Set up headers
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    
    // Set curl options
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, "PUT");
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json_payload);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10L);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    
    // Perform the request
    res = curl_easy_perform(curl);
    
    if (res != CURLE_OK) {
        LOG_ERROR("curl_easy_perform() failed for file storage API: %s", curl_easy_strerror(res));
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    long response_code;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);
    
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    
    if (response_code == 200) {
        LOG_INFO("Successfully created file via API: %s", response);
        send_log_to_logthon("INFO", "Successfully created file via file storage API");
        return 0;
    } else {
        LOG_ERROR("File storage API returned error code: %ld", response_code);
        send_log_to_logthon("ERROR", "Failed to create file via file storage API");
        return -1;
    }
}

// Background thread function to periodically create files
void* file_creation_thread(void* arg) {
    LOG_INFO("File creation thread started");
    
    while (1) {
        sleep(15); // Wait 15 seconds
        
        LOG_INFO("Creating file via API...");
        
        if (create_file_via_api() == 0) {
            LOG_INFO("File creation successful");
        } else {
            LOG_ERROR("File creation failed");
        }
    }
    
    return NULL;
}
