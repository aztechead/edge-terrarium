#include "vault.h"
#include "log_capture.h"

// Callback function for curl to write response data
size_t write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t realsize = size * nmemb;
    char* response = (char*)userp;
    
    // Find the current end of the string (null terminator)
    size_t current_len = strlen(response);
    size_t available_space = MAX_SECRET_SIZE - current_len - 1; // -1 for null terminator
    
    // Don't write more than available space
    if (realsize > available_space) {
        realsize = available_space;
    }
    
    // Copy the new data to the end of the existing string
    if (realsize > 0) {
        memcpy(response + current_len, contents, realsize);
        response[current_len + realsize] = '\0'; // Ensure null termination
    }
    
    return realsize;
}

// Function to retrieve a secret from Vault using enhanced authentication
int get_vault_secret(const char* secret_path, const char* key, char* output, size_t output_size) {
    // Try RBAC authentication first, fall back to static token
    if (get_vault_secret_rbac(secret_path, key, output, output_size) == 0) {
        return 0;
    }
    
    // Fall back to static token authentication
    return get_vault_secret_static(secret_path, key, output, output_size);
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
    // Log to logthon
    LOG_INFO("=== VAULT SECRETS RETRIEVED ===");
    LOG_INFO("API Key: %s", secrets->api_key);
    LOG_INFO("Database URL: %s", secrets->database_url);
    LOG_INFO("JWT Secret: %s", secrets->jwt_secret);
    LOG_INFO("Encryption Key: %s", secrets->encryption_key);
    LOG_INFO("Log Level: %s", secrets->log_level);
    LOG_INFO("Max Connections: %s", secrets->max_connections);
    LOG_INFO("=== END VAULT SECRETS ===");
    
    // Also print to stdout for Docker logs
    printf("=== VAULT SECRETS RETRIEVED ===\n");
    printf("API Key: %s\n", secrets->api_key);
    printf("Database URL: %s\n", secrets->database_url);
    printf("JWT Secret: %s\n", secrets->jwt_secret);
    printf("Encryption Key: %s\n", secrets->encryption_key);
    printf("Log Level: %s\n", secrets->log_level);
    printf("Max Connections: %s\n", secrets->max_connections);
    printf("=== END VAULT SECRETS ===\n");
    fflush(stdout);
}

// Quiet version that doesn't log the actual secret values
void log_vault_secrets_quiet(const vault_secrets_t* secrets) {
    LOG_INFO("Successfully retrieved all secrets from Vault");
}

// Function to read service account token from mounted volume
int read_service_account_token(char* token, size_t token_size) {
    const char* token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token";
    FILE* file = fopen(token_path, "r");
    
    if (!file) {
        // This is expected in Docker environment, so we'll be quiet about it
        return -1;
    }
    
    size_t bytes_read = fread(token, 1, token_size - 1, file);
    fclose(file);
    
    if (bytes_read == 0) {
        LOG_ERROR("Failed to read service account token");
        return -1;
    }
    
    token[bytes_read] = '\0';
    LOG_INFO("Successfully read service account token");
    return 0;
}

// Function to authenticate with Vault using Kubernetes auth
int authenticate_with_vault(char* vault_token, size_t token_size) {
    CURL* curl;
    CURLcode res;
    char url[512];
    char response[MAX_SECRET_SIZE] = {0};
    char service_account_token[4096];
    char* vault_addr;
    
    // Get Vault configuration from environment variables
    vault_addr = getenv("VAULT_ADDR");
    if (!vault_addr) {
        vault_addr = (char*)DEFAULT_VAULT_ADDR;
    }
    
    // Read service account token
    if (read_service_account_token(service_account_token, sizeof(service_account_token)) != 0) {
        return -1;
    }
    
    // Initialize curl
    curl = curl_easy_init();
    if (!curl) {
        LOG_ERROR("Failed to initialize curl for Vault authentication");
        return -1;
    }
    
    // Build the Vault auth URL
    snprintf(url, sizeof(url), "%s/v1/auth/kubernetes/login", vault_addr);
    
    // Build the request payload
    char payload[1024];
    snprintf(payload, sizeof(payload), 
        "{\"role\":\"custom-client-role\",\"jwt\":\"%s\"}", 
        service_account_token);
    
    // Set curl options
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10L);
    
    // Set content type header
    struct curl_slist* headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    
    // Perform the request
    res = curl_easy_perform(curl);
    
    if (res != CURLE_OK) {
        LOG_ERROR("curl_easy_perform() failed for Vault authentication: %s", curl_easy_strerror(res));
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Parse the JSON response
    json_object* json = json_tokener_parse(response);
    if (!json) {
        LOG_ERROR("Failed to parse JSON response from Vault authentication");
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Extract the client token
    json_object* auth_obj;
    json_object* client_token_obj;
    
    if (json_object_object_get_ex(json, "auth", &auth_obj) &&
        json_object_object_get_ex(auth_obj, "client_token", &client_token_obj)) {
        
        const char* client_token = json_object_get_string(client_token_obj);
        if (client_token) {
            strncpy(vault_token, client_token, token_size - 1);
            vault_token[token_size - 1] = '\0';
            LOG_INFO("Successfully authenticated with Vault using Kubernetes auth");
        } else {
            LOG_ERROR("Failed to get client token from Vault authentication response");
            json_object_put(json);
            curl_slist_free_all(headers);
            curl_easy_cleanup(curl);
            return -1;
        }
    } else {
        LOG_ERROR("Failed to find client_token in Vault authentication response");
        json_object_put(json);
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Cleanup
    json_object_put(json);
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    return 0;
}

// Function to retrieve a secret from Vault using RBAC authentication
int get_vault_secret_rbac(const char* secret_path, const char* key, char* output, size_t output_size) {
    CURL* curl;
    CURLcode res;
    char url[512];
    char response[MAX_SECRET_SIZE] = {0};
    char vault_token[4096];
    char* vault_addr;
    
    // Get Vault configuration from environment variables
    vault_addr = getenv("VAULT_ADDR");
    if (!vault_addr) {
        vault_addr = (char*)DEFAULT_VAULT_ADDR;
    }
    
    // Authenticate with Vault using Kubernetes auth
    if (authenticate_with_vault(vault_token, sizeof(vault_token)) != 0) {
        // This is expected in Docker environment, so we'll be quiet about it
        return -1;
    }
    
    // Initialize curl
    curl = curl_easy_init();
    if (!curl) {
        LOG_ERROR("Failed to initialize curl for secret retrieval");
        return -1;
    }
    
    // Build the Vault API URL
    snprintf(url, sizeof(url), "%s/v1/secret/data/%s", vault_addr, secret_path);
    
    // Build the authorization header
    char auth_header[256];
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
        LOG_ERROR("curl_easy_perform() failed for secret retrieval: %s", curl_easy_strerror(res));
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Parse the JSON response
    json_object* json = json_tokener_parse(response);
    if (!json) {
        LOG_ERROR("Failed to parse JSON response from Vault secret retrieval");
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
            LOG_INFO("Successfully retrieved secret '%s' using RBAC authentication", key);
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

// Function to retrieve a secret from Vault using static token authentication
int get_vault_secret_static(const char* secret_path, const char* key, char* output, size_t output_size) {
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
        LOG_ERROR("Failed to initialize curl for static token authentication");
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
        LOG_ERROR("curl_easy_perform() failed for static token authentication: %s", curl_easy_strerror(res));
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Parse the JSON response
    json_object* json = json_tokener_parse(response);
    if (!json) {
        LOG_ERROR("Failed to parse JSON response from Vault static token authentication");
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
            // Successfully retrieved secret, but we'll be quiet about it to reduce log noise
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
