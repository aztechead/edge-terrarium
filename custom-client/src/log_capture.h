#ifndef LOG_CAPTURE_H
#define LOG_CAPTURE_H

#include "common.h"

// Function declarations for log capture
void init_log_capture(void);
void cleanup_log_capture(void);
void log_printf(const char* level, const char* format, ...);
void log_message(const char* level, const char* message);

// Wrapper macros to replace printf calls
#define LOG_INFO(format, ...) log_printf("INFO", format, ##__VA_ARGS__)
#define LOG_ERROR(format, ...) log_printf("ERROR", format, ##__VA_ARGS__)
#define LOG_WARN(format, ...) log_printf("WARN", format, ##__VA_ARGS__)
#define LOG_DEBUG(format, ...) log_printf("DEBUG", format, ##__VA_ARGS__)

// Note: We don't override printf to avoid recursion issues
// Use LOG_INFO, LOG_ERROR, etc. macros instead

#endif // LOG_CAPTURE_H
