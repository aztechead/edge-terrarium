#ifndef VAULT_H
#define VAULT_H

#include "common.h"

// Function declarations for Vault integration
int get_vault_secret(const char* secret_path, const char* key, char* output, size_t output_size);
int get_vault_secret_rbac(const char* secret_path, const char* key, char* output, size_t output_size);
int get_vault_secret_static(const char* secret_path, const char* key, char* output, size_t output_size);
int authenticate_with_vault(char* vault_token, size_t token_size);
int read_service_account_token(char* token, size_t token_size);
int retrieve_vault_secrets(vault_secrets_t* secrets);
void log_vault_secrets(const vault_secrets_t* secrets);
void log_vault_secrets_quiet(const vault_secrets_t* secrets);

#endif // VAULT_H
