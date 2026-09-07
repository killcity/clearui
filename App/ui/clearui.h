/* SPDX-License-Identifier: Apache-2.0
 * Added for ClearUI in 2026.
 */

#ifndef UI_CLEARUI_H
#define UI_CLEARUI_H

#include <stdint.h>

const char *UI_CLEARUI_MenuItemName(uint8_t id);
void UI_DisplayClearUIMenu(void);
void UI_DisplayClearUIQuick(void);
void UI_DisplayClearUIScanGroup(void);
void UI_DisplayClearUIMain(void);
void UI_CLEARUI_RenderBackground(void);
void UI_CLEARUI_RenderBootLogo(void);
void UI_CLEARUI_TimeSlice10ms(void);
void UI_CLEARUI_TimeSlice500ms(void);
void UI_CLEARUI_DrawScopeMenu(const char *title, const char *const *labels,
                            uint8_t count, uint8_t selection);
void UI_CLEARUI_ShowToast(const char *text);

#endif
