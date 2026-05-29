#include "usarthmi_serial.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static const uint8_t k_terminator[3] = {0xFFu, 0xFFu, 0xFFu};

static int valid_ctx(const usarthmi_t *ctx) {
    return ctx != NULL && ctx->write != NULL;
}

static int valid_name(const char *text, int allow_dot) {
    const unsigned char *p = (const unsigned char *)text;
    if (p == NULL || *p == '\0') {
        return 0;
    }
    while (*p != '\0') {
        const unsigned char c = *p++;
        const int alpha = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z');
        const int digit = c >= '0' && c <= '9';
        if (!alpha && !digit && c != '_' && !(allow_dot && c == '.')) {
            return 0;
        }
    }
    return 1;
}

static int valid_text_value(const char *text) {
    const unsigned char *p = (const unsigned char *)text;
    if (p == NULL) {
        return 0;
    }
    while (*p != '\0') {
        if (*p == '"' || *p < 0x20u || *p == 0xFFu) {
            return 0;
        }
        ++p;
    }
    return 1;
}

static int send_format(usarthmi_t *ctx, const char *fmt, ...) {
    char cmd[USARTHMI_MAX_CMD_LEN];
    va_list ap;
    int n;

    if (!valid_ctx(ctx) || fmt == NULL) {
        return USARTHMI_ERR_ARGUMENT;
    }

    va_start(ap, fmt);
    n = vsnprintf(cmd, sizeof(cmd), fmt, ap);
    va_end(ap);

    if (n < 0) {
        return USARTHMI_ERR_PARSE;
    }
    if ((size_t)n >= sizeof(cmd)) {
        return USARTHMI_ERR_TOO_LONG;
    }
    return usarthmi_send_cmd(ctx, cmd);
}

void usarthmi_init(usarthmi_t *ctx, usarthmi_write_fn write, void *user) {
    if (ctx == NULL) {
        return;
    }
    ctx->write = write;
    ctx->user = user;
}

int usarthmi_send_raw(usarthmi_t *ctx, const uint8_t *data, size_t len) {
    if (!valid_ctx(ctx) || (data == NULL && len != 0u)) {
        return USARTHMI_ERR_ARGUMENT;
    }
    if (len == 0u) {
        return USARTHMI_OK;
    }
    return ctx->write(data, len, ctx->user) == 0 ? USARTHMI_OK : USARTHMI_ERR_WRITE;
}

int usarthmi_send_cmd(usarthmi_t *ctx, const char *cmd) {
    size_t len;
    int rc;

    if (!valid_ctx(ctx) || cmd == NULL) {
        return USARTHMI_ERR_ARGUMENT;
    }

    len = strlen(cmd);
    rc = usarthmi_send_raw(ctx, (const uint8_t *)cmd, len);
    if (rc != USARTHMI_OK) {
        return rc;
    }
    return usarthmi_send_raw(ctx, k_terminator, sizeof(k_terminator));
}

int usarthmi_get(usarthmi_t *ctx, const char *expr) {
    if (!valid_name(expr, 1)) {
        return USARTHMI_ERR_ARGUMENT;
    }
    return send_format(ctx, "get %s", expr);
}

int usarthmi_page(usarthmi_t *ctx, const char *page) {
    if (!valid_name(page, 0)) {
        return USARTHMI_ERR_ARGUMENT;
    }
    return send_format(ctx, "page %s", page);
}

int usarthmi_ref(usarthmi_t *ctx, const char *object) {
    if (!valid_name(object, 0)) {
        return USARTHMI_ERR_ARGUMENT;
    }
    return send_format(ctx, "ref %s", object);
}

int usarthmi_vis(usarthmi_t *ctx, const char *object, int visible) {
    if (!valid_name(object, 0)) {
        return USARTHMI_ERR_ARGUMENT;
    }
    return send_format(ctx, "vis %s,%u", object, visible ? 1u : 0u);
}

int usarthmi_tsw(usarthmi_t *ctx, const char *object, int enabled) {
    if (!valid_name(object, 0)) {
        return USARTHMI_ERR_ARGUMENT;
    }
    return send_format(ctx, "tsw %s,%u", object, enabled ? 1u : 0u);
}

int usarthmi_click(usarthmi_t *ctx, const char *object, int pressed) {
    if (!valid_name(object, 0)) {
        return USARTHMI_ERR_ARGUMENT;
    }
    return send_format(ctx, "click %s,%u", object, pressed ? 1u : 0u);
}

int usarthmi_dim(usarthmi_t *ctx, uint8_t value) {
    if (value > 100u) {
        return USARTHMI_ERR_ARGUMENT;
    }
    return send_format(ctx, "dim=%u", (unsigned)value);
}

int usarthmi_bkcmd(usarthmi_t *ctx, uint8_t mode) {
    if (mode > 3u) {
        return USARTHMI_ERR_ARGUMENT;
    }
    return send_format(ctx, "bkcmd=%u", (unsigned)mode);
}

int usarthmi_set_number(usarthmi_t *ctx, const char *object, const char *attr, int32_t value) {
    if (!valid_name(object, 0) || !valid_name(attr, 0)) {
        return USARTHMI_ERR_ARGUMENT;
    }
    return send_format(ctx, "%s.%s=%ld", object, attr, (long)value);
}

int usarthmi_set_value(usarthmi_t *ctx, const char *object, int32_t value) {
    return usarthmi_set_number(ctx, object, "val", value);
}

int usarthmi_set_text(usarthmi_t *ctx, const char *object, const char *attr, const char *value) {
    if (!valid_name(object, 0) || !valid_name(attr, 0) || !valid_text_value(value)) {
        return USARTHMI_ERR_ARGUMENT;
    }
    return send_format(ctx, "%s.%s=\"%s\"", object, attr, value);
}

int usarthmi_set_txt(usarthmi_t *ctx, const char *object, const char *value) {
    return usarthmi_set_text(ctx, object, "txt", value);
}

int usarthmi_printh(usarthmi_t *ctx, const uint8_t *data, size_t len) {
    static const char hex[] = "0123456789ABCDEF";
    char cmd[USARTHMI_MAX_CMD_LEN];
    size_t pos = 6u;
    size_t i;

    if (!valid_ctx(ctx) || (data == NULL && len != 0u)) {
        return USARTHMI_ERR_ARGUMENT;
    }
    if (len == 0u) {
        return USARTHMI_ERR_ARGUMENT;
    }
    if (pos + len * 3u >= sizeof(cmd)) {
        return USARTHMI_ERR_TOO_LONG;
    }

    memcpy(cmd, "printh", 6u);
    for (i = 0; i < len; ++i) {
        cmd[pos++] = ' ';
        cmd[pos++] = hex[(data[i] >> 4) & 0x0Fu];
        cmd[pos++] = hex[data[i] & 0x0Fu];
    }
    cmd[pos] = '\0';
    return usarthmi_send_cmd(ctx, cmd);
}

void usarthmi_rx_init(usarthmi_rx_t *rx) {
    if (rx == NULL) {
        return;
    }
    rx->length = 0u;
}

int usarthmi_rx_feed(usarthmi_rx_t *rx, uint8_t byte, usarthmi_frame_t *out) {
    int rc;

    if (rx == NULL) {
        return USARTHMI_ERR_ARGUMENT;
    }
    if (rx->length >= sizeof(rx->buffer)) {
        rx->length = 0u;
        return USARTHMI_ERR_OVERFLOW;
    }

    rx->buffer[rx->length++] = byte;
    if (rx->length < 3u) {
        return USARTHMI_RX_INCOMPLETE;
    }
    if (rx->buffer[rx->length - 1u] != 0xFFu ||
        rx->buffer[rx->length - 2u] != 0xFFu ||
        rx->buffer[rx->length - 3u] != 0xFFu) {
        return USARTHMI_RX_INCOMPLETE;
    }

    rc = usarthmi_parse_frame(rx->buffer, rx->length, out);
    rx->length = 0u;
    return rc == USARTHMI_OK ? USARTHMI_RX_FRAME : rc;
}

int usarthmi_parse_frame(const uint8_t *frame, size_t len, usarthmi_frame_t *out) {
    size_t payload_len;

    if (frame == NULL || out == NULL || len < 4u) {
        return USARTHMI_ERR_ARGUMENT;
    }
    if (frame[len - 1u] != 0xFFu || frame[len - 2u] != 0xFFu || frame[len - 3u] != 0xFFu) {
        return USARTHMI_ERR_PARSE;
    }

    memset(out, 0, sizeof(*out));
    out->type = USARTHMI_FRAME_UNKNOWN;
    out->code = frame[0];
    payload_len = len - 3u;

    if (out->code == 0x01u && payload_len == 1u) {
        out->type = USARTHMI_FRAME_ACK;
        return USARTHMI_OK;
    }
    if (out->code == 0x65u && payload_len >= 4u) {
        out->type = USARTHMI_FRAME_TOUCH;
        out->page = frame[1];
        out->component = frame[2];
        out->event = frame[3];
        return USARTHMI_OK;
    }
    if (out->code == 0x66u && payload_len >= 2u) {
        out->type = USARTHMI_FRAME_PAGE_ID;
        out->page = frame[1];
        return USARTHMI_OK;
    }
    if (out->code == 0x70u && payload_len >= 1u) {
        out->type = USARTHMI_FRAME_STRING;
        out->data = &frame[1];
        out->length = payload_len - 1u;
        return USARTHMI_OK;
    }
    if (out->code == 0x71u && payload_len >= 5u) {
        uint32_t raw = (uint32_t)frame[1] |
                       ((uint32_t)frame[2] << 8) |
                       ((uint32_t)frame[3] << 16) |
                       ((uint32_t)frame[4] << 24);
        out->type = USARTHMI_FRAME_NUMBER;
        out->number = (int32_t)raw;
        return USARTHMI_OK;
    }
    if (out->code <= 0x24u) {
        out->type = USARTHMI_FRAME_ERROR;
        return USARTHMI_OK;
    }

    out->data = payload_len > 1u ? &frame[1] : NULL;
    out->length = payload_len > 1u ? payload_len - 1u : 0u;
    return USARTHMI_OK;
}
