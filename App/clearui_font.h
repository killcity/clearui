/* SPDX-License-Identifier: Apache-2.0 */
#ifndef CLEARUI_FONT_H
#define CLEARUI_FONT_H
#include <stdint.h>
#define CLEARUI_FONT_GLYPH_COUNT 95
#define CLEARUI_FONT_HEIGHT 14
#define CLEARUI_FONT_COLUMN_BYTES 2
extern const uint16_t gClearUIFontOffsets[CLEARUI_FONT_GLYPH_COUNT];
extern const uint8_t gClearUIFontWidths[CLEARUI_FONT_GLYPH_COUNT];
extern const uint8_t gClearUIFontData[];
extern const uint8_t gClearUIFontSmall[CLEARUI_FONT_GLYPH_COUNT * 6];
#endif
