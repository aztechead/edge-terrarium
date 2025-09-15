#include "log_capture.h"
#include "logging.h"
#include <stdarg.h>
#include <sys/time.h>

// Global variables for log capture
static int log_capture_initialized = 0;
static char service_name[64] = "service-sink";

void init_log_capture(void) {
    if (log_capture_initialized) {
        return;
    }
    
    // Set service name based on environment or default
    const char* env_service = getenv("SERVICE_NAME");
    if (env_service) {
        strncpy(service_name, env_service, sizeof(service_name) - 1);
        service_name[sizeof(service_name) - 1] = '\0';
    }
    
    log_capture_initialized = 1;
    
    // Send initialization log
    log_message("INFO", "Log capture system initialized");
}

void cleanup_log_capture(void) {
    if (log_capture_initialized) {
        log_message("INFO", "Log capture system shutting down");
        log_capture_initialized = 0;
    }
}

void log_printf(const char* level, const char* format, ...) {
    if (!log_capture_initialized) {
        init_log_capture();
    }
    
    char message[1024];
    va_list args;
    va_start(args, format);
    vsnprintf(message, sizeof(message), format, args);
    va_end(args);
    
    // Also print to stdout for container logs (use fputs to avoid recursion)
    fputs(message, stdout);
    fflush(stdout);
    
    // Send to logthon
    log_message(level, message);
}

void log_message(const char* level, const char* message) {
    if (!log_capture_initialized) {
        init_log_capture();
    }
    
    // Send to logthon using the existing logging infrastructure
    send_log_to_logthon(level, message);
}
