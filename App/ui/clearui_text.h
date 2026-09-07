/* SPDX-License-Identifier: Apache-2.0 */
#ifndef UI_CLEARUI_TEXT_H
#define UI_CLEARUI_TEXT_H

#include <stdbool.h>
#include <stdint.h>

/* Original regular-weight proportional pixel sans, drawn on an eight-pixel row. */
uint16_t UI_ClearTextWidth(const char *text, uint8_t count);
void UI_ClearTextLine(uint8_t *line, const char *text, uint8_t left,
                      uint8_t right, bool centered);
void UI_ClearText(const char *text, uint8_t left, uint8_t right,
                  uint8_t page, bool centered);

#endif
