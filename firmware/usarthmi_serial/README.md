# MCU USART HMI serial helper

`usarthmi_serial.c/.h` is a small C99 helper for MCU projects. It is intentionally
HAL-free: the application owns the UART driver and passes one write callback to
the library.

## Minimal STM32 HAL adapter

```c
#include "usarthmi_serial.h"

static int hmi_write(const uint8_t *data, size_t len, void *user) {
    UART_HandleTypeDef *huart = (UART_HandleTypeDef *)user;
    return HAL_UART_Transmit(huart, (uint8_t *)data, (uint16_t)len, 100) == HAL_OK ? 0 : -1;
}

static usarthmi_t hmi;

void app_hmi_init(UART_HandleTypeDef *huart) {
    usarthmi_init(&hmi, hmi_write, huart);
    usarthmi_bkcmd(&hmi, 2);
    usarthmi_page(&hmi, "page0");
}
```

## Common operations

```c
usarthmi_set_value(&hmi, "m0", 3300);
usarthmi_set_txt(&hmi, "status", "READY");
usarthmi_get(&hmi, "bkcmd");
usarthmi_ref(&hmi, "main_bar");
usarthmi_vis(&hmi, "alarm", 1);
usarthmi_tsw(&hmi, "b_start", 0);
usarthmi_click(&hmi, "b_start", 1);
```

Every command is sent as ASCII followed by `FF FF FF`.

## Receiving frames

Feed bytes from the UART RX interrupt, DMA idle callback, or polling loop into
`usarthmi_rx_feed`. When it returns `USARTHMI_RX_FRAME`, inspect the parsed
frame:

```c
static usarthmi_rx_t rx;

void app_hmi_on_rx(uint8_t byte) {
    usarthmi_frame_t frame;
    int rc = usarthmi_rx_feed(&rx, byte, &frame);
    if (rc != USARTHMI_RX_FRAME) {
        return;
    }

    if (frame.type == USARTHMI_FRAME_NUMBER) {
        int32_t value = frame.number;
        (void)value;
    } else if (frame.type == USARTHMI_FRAME_TOUCH && frame.event == 1) {
        /* page/component press event */
    }
}
```

The parser recognizes the usual `0x01` ack, `0x65` touch event, `0x66` page id,
`0x70` string, `0x71` number, and `0x00..0x24` error frames. Unknown frames are
returned as raw payloads so projects can handle new firmware-specific messages.
