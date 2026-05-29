#ifndef USARTHMI_SERIAL_H
#define USARTHMI_SERIAL_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifndef USARTHMI_MAX_CMD_LEN
#define USARTHMI_MAX_CMD_LEN 160u
#endif

#ifndef USARTHMI_RX_BUFFER_SIZE
#define USARTHMI_RX_BUFFER_SIZE 128u
#endif

typedef int (*usarthmi_write_fn)(const uint8_t *data, size_t len, void *user);

typedef struct {
    usarthmi_write_fn write;
    void *user;
} usarthmi_t;

typedef enum {
    USARTHMI_OK = 0,
    USARTHMI_RX_INCOMPLETE = 1,
    USARTHMI_RX_FRAME = 2,
    USARTHMI_ERR_ARGUMENT = -1,
    USARTHMI_ERR_WRITE = -2,
    USARTHMI_ERR_TOO_LONG = -3,
    USARTHMI_ERR_PARSE = -4,
    USARTHMI_ERR_OVERFLOW = -5
} usarthmi_status_t;

typedef enum {
    USARTHMI_FRAME_UNKNOWN = 0,
    USARTHMI_FRAME_ACK,
    USARTHMI_FRAME_ERROR,
    USARTHMI_FRAME_TOUCH,
    USARTHMI_FRAME_PAGE_ID,
    USARTHMI_FRAME_STRING,
    USARTHMI_FRAME_NUMBER
} usarthmi_frame_type_t;

typedef struct {
    usarthmi_frame_type_t type;
    uint8_t code;
    uint8_t page;
    uint8_t component;
    uint8_t event;
    int32_t number;
    const uint8_t *data;
    size_t length;
} usarthmi_frame_t;

typedef struct {
    uint8_t buffer[USARTHMI_RX_BUFFER_SIZE];
    size_t length;
} usarthmi_rx_t;

void usarthmi_init(usarthmi_t *ctx, usarthmi_write_fn write, void *user);

int usarthmi_send_raw(usarthmi_t *ctx, const uint8_t *data, size_t len);
int usarthmi_send_cmd(usarthmi_t *ctx, const char *cmd);
int usarthmi_get(usarthmi_t *ctx, const char *expr);
int usarthmi_page(usarthmi_t *ctx, const char *page);
int usarthmi_ref(usarthmi_t *ctx, const char *object);
int usarthmi_vis(usarthmi_t *ctx, const char *object, int visible);
int usarthmi_tsw(usarthmi_t *ctx, const char *object, int enabled);
int usarthmi_click(usarthmi_t *ctx, const char *object, int pressed);
int usarthmi_dim(usarthmi_t *ctx, uint8_t value);
int usarthmi_bkcmd(usarthmi_t *ctx, uint8_t mode);
int usarthmi_set_number(usarthmi_t *ctx, const char *object, const char *attr, int32_t value);
int usarthmi_set_value(usarthmi_t *ctx, const char *object, int32_t value);
int usarthmi_set_text(usarthmi_t *ctx, const char *object, const char *attr, const char *value);
int usarthmi_set_txt(usarthmi_t *ctx, const char *object, const char *value);
int usarthmi_printh(usarthmi_t *ctx, const uint8_t *data, size_t len);

void usarthmi_rx_init(usarthmi_rx_t *rx);
int usarthmi_rx_feed(usarthmi_rx_t *rx, uint8_t byte, usarthmi_frame_t *out);
int usarthmi_parse_frame(const uint8_t *frame, size_t len, usarthmi_frame_t *out);

#ifdef __cplusplus
}
#endif

#endif
