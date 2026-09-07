/* SPDX-License-Identifier: Apache-2.0
 * ClearUI C3 (2026): shared memory-group browsing and scanning.
 */
#include "app/clearui.h"
#include "app/chFrScanner.h"
#include "audio.h"
#include "driver/py25q16.h"
#include "misc.h"
#include "radio.h"
#include "settings.h"
#include "ui/ui.h"
#include "ui/clearui.h"

/* Unused tail of the existing C1 alias window; the C1 driver preserves it.
 * Names occupy 0x12000..0x1219b. This record does not change their format. */
#define GROUP_ADDRESS 0x0121A0u
static uint8_t groups[2] = {MR_CHANNELS_LIST + 1, MR_CHANNELS_LIST + 1};
static bool loaded;

uint8_t CLEARUI_GetGroup(uint8_t vfo)
{
    if (!loaded)
    {
        uint8_t data[8];
        PY25Q16_ReadBuffer(GROUP_ADDRESS, data, sizeof(data));
        if (data[0] == 'G' && data[1] == 'R' && data[2] == 'P' && data[3] == 1)
            for (uint8_t i = 0; i < 2; i++)
                if (data[4+i] >= 1 && data[4+i] <= MR_CHANNELS_LIST + 1 &&
                    (uint8_t)(data[4+i] ^ data[6+i]) == 0xFF)
                    groups[i] = data[4+i];
        loaded = true;
    }
    return groups[vfo & 1];
}

void CLEARUI_SyncGroup(void)
{
    gEeprom.SCAN_LIST_DEFAULT = CLEARUI_GetGroup(gEeprom.TX_VFO);
}

bool CLEARUI_ChannelInGroup(uint16_t channel, uint8_t group)
{
    if (group < 1 || group > MR_CHANNELS_LIST + 1 ||
        !IS_MR_CHANNEL(channel) || !RADIO_CheckValidChannel(channel, false, 0))
        return false;
    const uint8_t member = MR_GetChannelAttributes(channel)->scanlist;
    /* Fusion's shared/All membership belongs to every group. Unassigned
     * channels remain accessible under All channels. Ignore scan skips here. */
    return group == MR_CHANNELS_LIST + 1 || member == group ||
           member == MR_CHANNELS_LIST + 1;
}

uint16_t CLEARUI_FindGroupChannel(uint16_t start, int8_t direction, uint8_t group)
{
    for (uint16_t i = 0; i < MR_CHANNELS_MAX; i++, start += direction)
    {
        if (start == 0xFFFF)
            start = MR_CHANNEL_LAST;
        else if (!IS_MR_CHANNEL(start))
            start = MR_CHANNEL_FIRST;
        if (CLEARUI_ChannelInGroup(start, group))
            return start;
    }
    return 0xFFFF;
}

bool CLEARUI_SelectGroup(uint8_t group)
{
    const uint8_t vfo = gEeprom.TX_VFO;
    const uint16_t current = gEeprom.ScreenChannel[vfo];
    const uint16_t next = CLEARUI_FindGroupChannel(current, 1, group);
    if (next == 0xFFFF)
    {
        UI_CLEARUI_ShowToast("Group is empty");
        gBeepToPlay = BEEP_500HZ_60MS_DOUBLE_BEEP_OPTIONAL;
        gRequestDisplayScreen = DISPLAY_MAIN;
        return false;
    }
    if (CLEARUI_GetGroup(vfo) != group)
    {
        groups[vfo] = group;
        const uint8_t data[8] = {'G','R','P',1, groups[0], groups[1],
                                (uint8_t)~groups[0], (uint8_t)~groups[1]};
        PY25Q16_WriteBuffer(GROUP_ADDRESS, data, sizeof(data), false);
    }
    CLEARUI_SyncGroup();
    gRequestSaveSettings = true;
    if (IS_MR_CHANNEL(current) && next != current && gScanStateDir == SCAN_OFF)
    {
        gEeprom.MrChannel[vfo] = next;
        gEeprom.ScreenChannel[vfo] = next;
        gRequestSaveVFO = true;
        gVfoConfigureMode = VFO_CONFIGURE_RELOAD;
    }
    gUpdateDisplay = true;
    return true;
}
