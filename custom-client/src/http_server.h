#ifndef HTTP_SERVER_H
#define HTTP_SERVER_H

#include "common.h"

// Function declarations for HTTP server functionality
int parse_http_request(const char* request, http_request_t* req);
void send_http_response(int client_socket, int status_code, const char* message);
void handle_client(int client_socket, const char* client_ip);
int create_server_socket(int port);

#endif // HTTP_SERVER_H
