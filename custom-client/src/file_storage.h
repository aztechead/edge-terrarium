#ifndef FILE_STORAGE_H
#define FILE_STORAGE_H

#include "common.h"

// Function declarations for file storage integration
int create_file_via_api(void);
void* file_creation_thread(void* arg);

#endif // FILE_STORAGE_H
