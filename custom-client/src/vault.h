#ifndef VAULT_H
#define VAULT_H

#include "common.h"

// Function declarations for Vault integration
int get_vault_secret(const char* secret_path, const char* key, char* output, size_t output_size);
int retrieve_vault_secrets(vault_secrets_t* secrets);
void log_vault_secrets(const vault_secrets_t* secrets);

#endif // VAULT_H
