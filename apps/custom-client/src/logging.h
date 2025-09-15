#ifndef LOGGING_H
#define LOGGING_H

#include "common.h"

// Function declarations for logging
void send_log_to_logthon(const char* level, const char* message);
void log_request(const http_request_t* req, const char* client_ip);
void extract_query_params(const char* path, char* query_params, size_t query_params_size);

#endif // LOGGING_H
