/* ClearUI C1 modifications (2026): display, interaction and programming support. */

#ifdef VERSION_STRING
    #define VER     " "VERSION_STRING
#else
    #define VER     ""
#endif

#ifdef ENABLE_FEAT_F4HWN
#ifdef ENABLE_CLEAR_UI
    // Fits the programming protocol's 16-byte version field.
    /* v6 has different action IDs/capabilities. Reject legacy drivers. */
    const char Version[]         = "ClearUI C10";
#else
    const char Version[]         = AUTHOR_STRING_2 " " VERSION_STRING_2;
#endif
    const char DisplayVersion[]  = AUTHOR_STRING_2 " " DISPLAY_VERSION_STRING_2;
    const char Edition[]         = EDITION_STRING;
    const char BuildDate[]       = __DATE__;
    const char BuildTime[]       = __TIME__;
    const char BuildCommit[]     = BUILD_COMMIT;
#else
    const char Version[]      = AUTHOR_STRING VER;
#endif

const char UART_Version[] = "UV-K5 Firmware, " AUTHOR_STRING VER "\r\n";
