#include "vault.h"
#include "log_capture.h"

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
        LOG_ERROR("Failed to initialize curl");
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
        LOG_ERROR("curl_easy_perform() failed: %s", curl_easy_strerror(res));
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Parse the JSON response
    json_object* json = json_tokener_parse(response);
    if (!json) {
        LOG_ERROR("Failed to parse JSON response from Vault");
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
            LOG_ERROR("Failed to get string value for key: %s", key);
            json_object_put(json);
            curl_easy_cleanup(curl);
            return -1;
        }
    } else {
        LOG_ERROR("Failed to find key '%s' in Vault response", key);
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
    LOG_INFO("Retrieving secrets from Vault...");
    
    int success = 1;
    
    // Retrieve configuration secrets
    if (get_vault_secret("custom-client/config", "api_key", secrets->api_key, sizeof(secrets->api_key)) != 0) {
        LOG_ERROR("Failed to retrieve api_key from Vault");
        success = 0;
    }
    
    if (get_vault_secret("custom-client/config", "database_url", secrets->database_url, sizeof(secrets->database_url)) != 0) {
        LOG_ERROR("Failed to retrieve database_url from Vault");
        success = 0;
    }
    
    if (get_vault_secret("custom-client/config", "jwt_secret", secrets->jwt_secret, sizeof(secrets->jwt_secret)) != 0) {
        LOG_ERROR("Failed to retrieve jwt_secret from Vault");
        success = 0;
    }
    
    if (get_vault_secret("custom-client/config", "encryption_key", secrets->encryption_key, sizeof(secrets->encryption_key)) != 0) {
        LOG_ERROR("Failed to retrieve encryption_key from Vault");
        success = 0;
    }
    
    if (get_vault_secret("custom-client/config", "log_level", secrets->log_level, sizeof(secrets->log_level)) != 0) {
        LOG_ERROR("Failed to retrieve log_level from Vault");
        success = 0;
    }
    
    if (get_vault_secret("custom-client/config", "max_connections", secrets->max_connections, sizeof(secrets->max_connections)) != 0) {
        LOG_ERROR("Failed to retrieve max_connections from Vault");
        success = 0;
    }
    
    if (success) {
        LOG_INFO("Successfully retrieved all secrets from Vault");
    } else {
        LOG_WARN("Some secrets could not be retrieved from Vault");
    }
    
    return success ? 0 : -1;
}

// Function to log retrieved secrets (for demonstration)
void log_vault_secrets(const vault_secrets_t* secrets) {
    LOG_INFO("=== VAULT SECRETS RETRIEVED ===");
    LOG_INFO("API Key: %s", secrets->api_key);
    LOG_INFO("Database URL: %s", secrets->database_url);
    LOG_INFO("JWT Secret: %s", secrets->jwt_secret);
    LOG_INFO("Encryption Key: %s", secrets->encryption_key);
    LOG_INFO("Log Level: %s", secrets->log_level);
    LOG_INFO("Max Connections: %s", secrets->max_connections);
    LOG_INFO("=== END VAULT SECRETS ===");
}
